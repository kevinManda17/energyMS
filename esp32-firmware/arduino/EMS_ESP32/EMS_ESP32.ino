/*
  EMS IoT — Firmware ESP32 « 3 lignes » (prototype mémoire)

  Rôle :
   - lire 3 capteurs de tension ZMPT101B + 3 capteurs de courant ZMCT103C ;
   - calculer tension / courant / puissance RMS par ligne ;
   - commander 3 relais (lignes 1 à 3) en mode manuel (Serial) ou
     automatique (règles locales, ou système expert backend via HTTP) ;
   - publier les mesures en JSON sur le port série (115200 bauds).

  Sécurité :
   - tous les relais OFF au démarrage (niveau inactif fixé AVANT pinMode
     pour éviter le claquement des relais actifs-LOW pendant le boot) ;
   - garde-fou local appliqué à TOUTE décision automatique, y compris
     celle du backend : une ligne en surcharge n'est jamais activée ;
   - backend muet : dernier état conservé, puis délestage de la ligne
     non prioritaire (L2) après BACKEND_MAX_FAILURES échecs consécutifs.

  Toute la configuration (pins, calibration, seuils, Wi-Fi) : config.h
  (onglet à côté de ce fichier — Arduino IDE le compile automatiquement,
  aucun copier-coller n'est nécessaire tant que les deux fichiers restent
  dans le même dossier de croquis).
*/

#include <Arduino.h>
#include "config.h"

#if USE_WIFI
#include <WiFi.h>
#include <HTTPClient.h>
#endif

/* ==================== ETAT GLOBAL ==================== */

struct LineData {
  float vSensorRms = 0.0f;  // RMS brut sortie ZMPT101B (V)
  float iSensorRms = 0.0f;  // RMS brut sortie ZMCT103C (V)
  float voltage    = 0.0f;  // tension ligne calibrée (V AC)
  float current    = 0.0f;  // courant ligne calibré (A AC)
  float power      = 0.0f;  // puissance apparente estimée (W)
};

struct Decision {
  bool l1 = false;
  bool l2 = false;
  bool l3 = false;
};

/* Sans Wi-Fi : démarrage en mode manuel (pilotage série uniquement).
   Avec Wi-Fi : démarrage en mode auto pour que l'appareil soit
   commandable à distance depuis les interfaces dès le boot (les relais
   restent malgré tout OFF tant que le premier sondage backend n'a pas
   répondu — cf. initRelayPin + applyRelays(false...) dans setup()). */
bool manualMode   = (USE_WIFI == 0);
bool relayL1State = false;
bool relayL2State = false;
bool relayL3State = false;

LineData lastLine1, lastLine2, lastLine3;  // dernières mesures (pour "status")

uint8_t backendFailures = 0;

unsigned long lastMeasureMs = 0;

/* ==================== RELAIS ==================== */

void writeRelay(uint8_t pin, bool on) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
}

void applyRelays(bool l1, bool l2, bool l3) {
  relayL1State = l1;
  relayL2State = l2;
  relayL3State = l3;
  writeRelay(RELAY_L1_PIN, relayL1State);
  writeRelay(RELAY_L2_PIN, relayL2State);
  writeRelay(RELAY_L3_PIN, relayL3State);
}

void setLineRelay(int line, bool state) {
  switch (line) {
    case 1: relayL1State = state; writeRelay(RELAY_L1_PIN, state); break;
    case 2: relayL2State = state; writeRelay(RELAY_L2_PIN, state); break;
    case 3: relayL3State = state; writeRelay(RELAY_L3_PIN, state); break;
    default: break;
  }
}

/* Fixe le niveau INACTIF sur la pin avant de la passer en sortie :
   évite l'impulsion parasite au boot sur les modules actifs-LOW. */
void initRelayPin(uint8_t pin) {
  digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW);
  pinMode(pin, OUTPUT);
  digitalWrite(pin, RELAY_ACTIVE_LOW ? HIGH : LOW);
}

/* ==================== LECTURE RMS ==================== */

/* RMS de la composante AC (l'offset DC des capteurs est retiré via la
   variance : RMS_AC = sqrt(E[x²] - E[x]²)). Renvoie des volts côté ADC. */
float readSensorRmsVoltage(uint8_t pin) {
  double sum = 0.0;
  double sumSq = 0.0;

  for (int i = 0; i < RMS_SAMPLES; i++) {
    int raw = analogRead(pin);
    sum += raw;
    sumSq += (double)raw * (double)raw;
    delayMicroseconds(SAMPLE_DELAY_US);
  }

  double mean = sum / RMS_SAMPLES;
  double variance = (sumSq / RMS_SAMPLES) - (mean * mean);
  if (variance < 0.0) variance = 0.0;

  return (float)(sqrt(variance) * ADC_REF_V / ADC_MAX);
}

LineData readLine(uint8_t pinV, uint8_t pinI, float calV, float calI) {
  LineData data;
  data.vSensorRms = readSensorRmsVoltage(pinV);
  data.iSensorRms = readSensorRmsVoltage(pinI);
  data.voltage = data.vSensorRms * calV;
  data.current = data.iSensorRms * calI;
  data.power   = data.voltage * data.current;
  return data;
}

/* ==================== SECURITE & REGLES LOCALES ==================== */

/* Garde-fou appliqué à toute décision automatique (locale OU backend) :
   jamais d'activation d'une ligne si la logique de surcharge l'interdit. */
Decision clampDecision(Decision d, const LineData& l1, const LineData& l2,
                       const LineData& l3) {
  const float totalPower = l1.power + l2.power + l3.power;

  if (l1.power > MAX_LINE_POWER_W) d.l1 = false;
  if (l2.power > MAX_LINE_POWER_W) d.l2 = false;
  if (l3.power > MAX_LINE_POWER_W) d.l3 = false;

  if (totalPower > MAX_TOTAL_POWER_W) d.l2 = false;           // L2 : non prioritaire
  if (l1.power + l3.power > MAX_TOTAL_POWER_W) d.l1 = false;  // L1 : moyenne priorité
  if (l3.power > MAX_TOTAL_POWER_W) {                         // dernier recours
    d.l1 = false;
    d.l2 = false;
    d.l3 = false;
  }
  return d;
}

/* Règles locales provisoires (secours / test sans backend).
   Priorités : L3 prioritaire, L1 moyenne, L2 non prioritaire. */
Decision localExpertDecision(const LineData& l1, const LineData& l2,
                             const LineData& l3) {
  Decision d;
  d.l1 = true;
  d.l2 = true;
  d.l3 = true;
  return clampDecision(d, l1, l2, l3);
}

/* ==================== BACKEND ==================== */

#if USE_WIFI
/* Réponse attendue : "L1=1;L2=0;L3=1" (espaces/casse tolérés). */
bool parseDecisionText(String response, Decision& d) {
  response.toUpperCase();
  response.replace(" ", "");

  int p1 = response.indexOf("L1=");
  int p2 = response.indexOf("L2=");
  int p3 = response.indexOf("L3=");
  if (p1 < 0 || p2 < 0 || p3 < 0) return false;

  d.l1 = response.substring(p1 + 3, p1 + 4).toInt() == 1;
  d.l2 = response.substring(p2 + 3, p2 + 4).toInt() == 1;
  d.l3 = response.substring(p3 + 3, p3 + 4).toInt() == 1;
  return true;
}

String buildMeasurementsPayload(const LineData& l1, const LineData& l2,
                                const LineData& l3) {
  String payload = "{";
  payload += "\"line1\":{\"voltage\":" + String(l1.voltage, 3) +
             ",\"current\":" + String(l1.current, 3) +
             ",\"power\":" + String(l1.power, 3) + "},";
  payload += "\"line2\":{\"voltage\":" + String(l2.voltage, 3) +
             ",\"current\":" + String(l2.current, 3) +
             ",\"power\":" + String(l2.power, 3) + "},";
  payload += "\"line3\":{\"voltage\":" + String(l3.voltage, 3) +
             ",\"current\":" + String(l3.current, 3) +
             ",\"power\":" + String(l3.power, 3) + "}";
  payload += "}";
  return payload;
}

/* Interroge le backend. En cas d'échec : conserve le dernier état connu,
   puis coupe la ligne non prioritaire (L2) après plusieurs échecs. */
Decision backendDecision(const LineData& l1, const LineData& l2,
                         const LineData& l3) {
  Decision d;
  d.l1 = relayL1State;
  d.l2 = relayL2State;
  d.l3 = relayL3State;

  bool ok = false;
  bool wifiUp = (WiFi.status() == WL_CONNECTED);
  int httpCode = 0;  // 0 = aucune tentative (Wi-Fi coupe)

  if (wifiUp) {
    HTTPClient http;
    http.setTimeout(HTTP_TIMEOUT_MS);
    http.setConnectTimeout(HTTP_TIMEOUT_MS);
    if (http.begin(BACKEND_DECISION_URL)) {
      http.addHeader("Content-Type", "application/json");
      httpCode = http.POST(buildMeasurementsPayload(l1, l2, l3));
      if (httpCode >= 200 && httpCode < 300) {
        Decision received;
        if (parseDecisionText(http.getString(), received)) {
          d = received;
          ok = true;
        }
      }
      http.end();
    }
  }

  if (ok) {
    backendFailures = 0;
  } else {
    if (backendFailures < 255) backendFailures++;
    if (backendFailures >= BACKEND_MAX_FAILURES) {
      d.l2 = false;  // délestage de précaution : ligne non prioritaire
    }
    /* Diagnostic explicite :
         wifi=0            -> pas connecte au Wi-Fi (2,4 GHz / identifiants)
         wifi=1, http<=0   -> serveur injoignable (pare-feu / mauvaise IP / VPN)
         wifi=1, http=404  -> mauvaise route backend
         wifi=1, http=200  -> reponse recue mais format inattendu             */
    Serial.print("{\"warning\":\"backend_unreachable\",\"wifi\":");
    Serial.print(wifiUp ? 1 : 0);
    Serial.print(",\"ip\":\"");
    Serial.print(wifiUp ? WiFi.localIP().toString() : String("-"));
    Serial.print("\",\"http\":");
    Serial.print(httpCode);
    Serial.print(",\"failures\":");
    Serial.print(backendFailures);
    Serial.println("}");
  }

  return d;
}

void ensureWifi() {
  static unsigned long lastAttemptMs = 0;
  static bool wasConnected = false;

  if (WiFi.status() == WL_CONNECTED) {
    if (!wasConnected) {           // transition : on vient de se connecter
      wasConnected = true;
      Serial.print("WiFi connecte. IP : ");
      Serial.println(WiFi.localIP());
    }
    return;
  }

  wasConnected = false;
  unsigned long now = millis();
  if (now - lastAttemptMs < 10000) return;  // nouvelle tentative toutes les 10 s
  lastAttemptMs = now;
  Serial.println("WiFi non connecte, nouvelle tentative...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}
#endif  // USE_WIFI

/* ==================== AFFICHAGE SERIAL ==================== */

void printLineJson(const char* name, const LineData& l, bool last = false) {
  Serial.print("\"");
  Serial.print(name);
  Serial.print("\":{");
  Serial.print("\"vSensorRms\":"); Serial.print(l.vSensorRms, 4); Serial.print(",");
  Serial.print("\"iSensorRms\":"); Serial.print(l.iSensorRms, 4); Serial.print(",");
  Serial.print("\"voltage\":");    Serial.print(l.voltage, 3);    Serial.print(",");
  Serial.print("\"current\":");    Serial.print(l.current, 3);    Serial.print(",");
  Serial.print("\"power\":");      Serial.print(l.power, 3);
  Serial.print("}");
  if (!last) Serial.print(",");
}

void printMeasurements(const LineData& l1, const LineData& l2,
                       const LineData& l3) {
  const float totalPower = l1.power + l2.power + l3.power;

  Serial.print("{");
  Serial.print("\"mode\":\"");
  Serial.print(manualMode ? "manual" : "auto");
  Serial.print("\",");

  Serial.print("\"relays\":{");
  Serial.print("\"l1\":"); Serial.print(relayL1State ? 1 : 0); Serial.print(",");
  Serial.print("\"l2\":"); Serial.print(relayL2State ? 1 : 0); Serial.print(",");
  Serial.print("\"l3\":"); Serial.print(relayL3State ? 1 : 0);
  Serial.print("},");

  printLineJson("line1", l1);
  printLineJson("line2", l2);
  printLineJson("line3", l3, true);   // last=true : pas de virgule en trop
  Serial.print(",\"totalPower\":");
  Serial.print(totalPower, 3);
  Serial.println("}");
}

/* ==================== COMMANDES SERIAL ==================== */
/* on 1 | off 1 | on 2 | off 2 | on 3 | off 3
   all on | all off | auto | manual | status | help                       */

void printHelp() {
  Serial.println("Commandes : on 1, off 1, on 2, off 2, on 3, off 3,");
  Serial.println("            all on, all off, auto, manual, status, help");
}

void executeCommand(String cmd) {
  cmd.trim();
  cmd.toLowerCase();

  if (cmd == "on 1") {
    manualMode = true; setLineRelay(1, true);  Serial.println("Ligne 1 ON");
  } else if (cmd == "off 1") {
    manualMode = true; setLineRelay(1, false); Serial.println("Ligne 1 OFF");
  } else if (cmd == "on 2") {
    manualMode = true; setLineRelay(2, true);  Serial.println("Ligne 2 ON");
  } else if (cmd == "off 2") {
    manualMode = true; setLineRelay(2, false); Serial.println("Ligne 2 OFF");
  } else if (cmd == "on 3") {
    manualMode = true; setLineRelay(3, true);  Serial.println("Ligne 3 ON");
  } else if (cmd == "off 3") {
    manualMode = true; setLineRelay(3, false); Serial.println("Ligne 3 OFF");
  } else if (cmd == "all on") {
    manualMode = true; applyRelays(true, true, true);   Serial.println("Toutes les lignes ON");
  } else if (cmd == "all off") {
    manualMode = true; applyRelays(false, false, false); Serial.println("Toutes les lignes OFF");
  } else if (cmd == "auto") {
    manualMode = false; Serial.println("Mode automatique active");
  } else if (cmd == "manual") {
    manualMode = true;  Serial.println("Mode manuel active");
  } else if (cmd == "status") {
    printMeasurements(lastLine1, lastLine2, lastLine3);
  } else if (cmd == "help") {
    printHelp();
  } else {
    Serial.println("Commande inconnue");
    printHelp();
  }
}

/* Lecture non bloquante : les caractères sont accumulés au fil de l'eau,
   la commande est exécutée à la fin de ligne (\n ou \r). */
void handleSerialCommand() {
  static String buffer;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (buffer.length() > 0) {
        executeCommand(buffer);
        buffer = "";
      }
    } else if (buffer.length() < 32) {
      buffer += c;
    }
  }
}

/* ==================== SETUP / LOOP ==================== */

void setup() {
  Serial.begin(115200);
  delay(1000);

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  /* Sécurité : relais OFF avant toute chose. */
  initRelayPin(RELAY_L1_PIN);
  initRelayPin(RELAY_L2_PIN);
  initRelayPin(RELAY_L3_PIN);
  applyRelays(false, false, false);

#if USE_WIFI
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connexion WiFi");

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connecte. IP : ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi non connecte. Le systeme reste utilisable en local.");
  }
#endif

  Serial.println("EMS ESP32 pret.");
  Serial.print("Mode initial : ");
  Serial.println(manualMode ? "manuel (pilotage serie)"
                 : "auto (pilote par le backend)");
  Serial.println("Relais OFF au demarrage. Test relais : on 1, off 1, ...");
  printHelp();
}

void loop() {
  handleSerialCommand();

#if USE_WIFI
  ensureWifi();
#endif

  unsigned long now = millis();
  if (now - lastMeasureMs >= MEASURE_INTERVAL_MS) {
    lastMeasureMs = now;

    lastLine1 = readLine(PIN_V1, PIN_I1, CAL_V1, CAL_I1);
    lastLine2 = readLine(PIN_V2, PIN_I2, CAL_V2, CAL_I2);
    lastLine3 = readLine(PIN_V3, PIN_I3, CAL_V3, CAL_I3);

    printMeasurements(lastLine1, lastLine2, lastLine3);

    if (!manualMode) {
#if USE_WIFI
      Decision d = backendDecision(lastLine1, lastLine2, lastLine3);
#else
      Decision d = localExpertDecision(lastLine1, lastLine2, lastLine3);
#endif
      /* Garde-fou final : même une décision backend ne peut pas activer
         une ligne que la logique de surcharge interdit. */
      d = clampDecision(d, lastLine1, lastLine2, lastLine3);
      applyRelays(d.l1, d.l2, d.l3);
    }
  }
}
