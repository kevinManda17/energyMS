// ============================================================================
//  EMS IoT — Nœud PRINCIPAL (AC)
//  ----------------------------------------------------------------------------
//  Rôle    : mesurer 3 lignes AC (tension/courant), commander 3 relais,
//            recevoir les mesures DC du nœud secondaire par UART, et tout
//            remonter au backend.
//  Contrôle: MQTT (commande + état des relais) — plan de contrôle principal.
//  Données : HTTP POST périodique (AC + DC) vers le backend -> système expert.
//
//  Cible   : ESP32 WROOM-32 (carte "ESP32 Dev Module").
//  Dépend. : PubSubClient (Nick O'Leary). WiFi/HTTPClient : inclus dans le core.
//
//  Dossier de sketch : EMS_ESP32_Principal/  contenant en plus
//                      config.h, secrets.h.
// ============================================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>

#include "config.h"
#include "secrets.h"

// ---------------------------------------------------------------------------
//  État global
// ---------------------------------------------------------------------------
WiFiClient   net;
PubSubClient mqtt(net);

const int  vPins[3]     = { PIN_V_L1, PIN_V_L2, PIN_V_L3 };
const int  iPins[3]     = { PIN_I_L1, PIN_I_L2, PIN_I_L3 };
const int  relayPins[3] = { PIN_RELAY_L1, PIN_RELAY_L2, PIN_RELAY_L3 };
bool       lineOn[3]    = { false, false, false };

// Mesures DC reçues du nœud secondaire par UART (dernières valeurs connues)
struct DcData { float iPV, iBAT1, iBAT2, vPV, vREG, vBAT, tBAT1, tBAT2, tPV; };
DcData   dc      = {};
uint32_t dcLastMs = 0;
bool     dcEver   = false;

static const char* lineName(int i) { static const char* n[3] = {"L1","L2","L3"}; return n[i]; }

// ---------------------------------------------------------------------------
//  Relais — on raisonne en "ligne alimentée / coupée", jamais en niveau
//  électrique. RELAY_ACTIVE_LOW (config.h) fait la traduction.
// ---------------------------------------------------------------------------
static inline int relayLevel(bool on) {
#if RELAY_ACTIVE_LOW
  return on ? LOW : HIGH;
#else
  return on ? HIGH : LOW;
#endif
}

String topicLineBase()   { return String(MQTT_TOPIC_PREFIX) + "/" + HOUSE_ID + "/lines/"; }
String topicState(int i) { return topicLineBase() + lineName(i) + "/state"; }
String topicSetWildcard(){ return topicLineBase() + "+/set"; }
String topicStatus()     { return String(MQTT_TOPIC_PREFIX) + "/" + HOUSE_ID + "/node/principal/status"; }

void publishLineState(int i) {
  if (!mqtt.connected()) return;
  mqtt.publish(topicState(i).c_str(), lineOn[i] ? "1" : "0", true /* retenu */);
}

void setLine(int i, bool on) {
  lineOn[i] = on;
  digitalWrite(relayPins[i], relayLevel(on));
  Serial.printf("[RELAIS] %s -> %s\n", lineName(i), on ? "ON" : "OFF");
  publishLineState(i);
}

// ---------------------------------------------------------------------------
//  MQTT
// ---------------------------------------------------------------------------
int lineIndexFromSetTopic(const String& t) {
  for (int i = 0; i < 3; i++)
    if (t == topicLineBase() + lineName(i) + "/set") return i;
  return -1;
}

void onMqttMessage(char* topic, byte* payload, unsigned int len) {
  String t(topic), msg;
  msg.reserve(len);
  for (unsigned int k = 0; k < len; k++) msg += (char)payload[k];
  msg.trim();

  int i = lineIndexFromSetTopic(t);
  if (i < 0) return;

  bool on;
  if (msg == "1" || msg.equalsIgnoreCase("on")  || msg.equalsIgnoreCase("true"))  on = true;
  else if (msg == "0" || msg.equalsIgnoreCase("off") || msg.equalsIgnoreCase("false")) on = false;
  else if (msg.equalsIgnoreCase("toggle")) on = !lineOn[i];
  else { Serial.printf("[MQTT] payload ignoré sur %s : '%s'\n", topic, msg.c_str()); return; }

  Serial.printf("[MQTT] commande %s = %s\n", lineName(i), on ? "ON" : "OFF");
  setLine(i, on);
}

void mqttEnsureConnected() {
  if (mqtt.connected()) return;

  static uint32_t lastTry = 0;
  if (millis() - lastTry < 3000) return;   // ne pas marteler le broker
  lastTry = millis();

  String cid = String("ems-principal-") + HOUSE_ID + "-" +
               String((uint32_t)ESP.getEfuseMac(), HEX);

  bool ok;
  if (strlen(MQTT_USER) > 0)
    ok = mqtt.connect(cid.c_str(), MQTT_USER, MQTT_PASSWORD,
                      topicStatus().c_str(), 0, true, "offline");
  else
    ok = mqtt.connect(cid.c_str(), nullptr, nullptr,
                      topicStatus().c_str(), 0, true, "offline");

  if (ok) {
    Serial.println("[MQTT] connecté");
    mqtt.publish(topicStatus().c_str(), "online", true);
    mqtt.subscribe(topicSetWildcard().c_str());
    for (int i = 0; i < 3; i++) publishLineState(i);   // état courant (retenu)
  } else {
    Serial.printf("[MQTT] échec (rc=%d), nouvel essai bientôt\n", mqtt.state());
  }
}

// ---------------------------------------------------------------------------
//  WiFi
// ---------------------------------------------------------------------------
void wifiEnsureConnected() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("[WiFi] connexion à \"%s\" ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) { delay(250); Serial.print("."); }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
    Serial.printf("[WiFi] OK, IP = %s\n", WiFi.localIP().toString().c_str());
  else
    Serial.println("[WiFi] échec (nouvel essai plus tard)");
}

// ---------------------------------------------------------------------------
//  UART — réception des mesures DC du nœud secondaire
//  Trame : $DC,i1,i2,i3,v1,v2,v3,t1,t2,t3*CK\n
//  CK = XOR (hex) de tout ce qui est entre '$' et '*'.  LE FORMAT DOIT ÊTRE
//  IDENTIQUE côté secondaire.
// ---------------------------------------------------------------------------
bool parseDcFrame(const String& line) {
  if (!line.startsWith("$")) return false;
  int star = line.indexOf('*');
  if (star < 2) return false;

  String payload = line.substring(1, star);
  uint8_t ck = 0;
  for (size_t i = 0; i < payload.length(); i++) ck ^= (uint8_t)payload[i];
  uint8_t given = (uint8_t)strtol(line.substring(star + 1).c_str(), nullptr, 16);
  if (ck != given) { Serial.println("[UART] checksum invalide, trame jetée"); return false; }

  DcData d;
  int n = sscanf(payload.c_str(), "DC,%f,%f,%f,%f,%f,%f,%f,%f,%f",
                 &d.iPV, &d.iBAT1, &d.iBAT2, &d.vPV, &d.vREG, &d.vBAT,
                 &d.tBAT1, &d.tBAT2, &d.tPV);
  if (n != 9) return false;

  dc = d; dcLastMs = millis(); dcEver = true;
  return true;
}

void readUart() {
  static char   buf[160];
  static size_t len = 0;

  while (Serial2.available()) {
    char c = (char)Serial2.read();
    if (c == '\n' || c == '\r') {
      if (len > 0) {
        buf[len] = '\0';
        if (parseDcFrame(String(buf)))
          Serial.printf("[UART] DC : Ipv=%.3f Ibat1=%.3f Ibat2=%.3f | "
                        "Vpv=%.2f Vreg=%.2f Vbat=%.2f | Tbat1=%.1f Tbat2=%.1f Tpv=%.1f\n",
                        dc.iPV, dc.iBAT1, dc.iBAT2, dc.vPV, dc.vREG, dc.vBAT,
                        dc.tBAT1, dc.tBAT2, dc.tPV);
        len = 0;
      }
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = c;
    } else {
      len = 0;   // trame trop longue : on repart proprement
    }
  }
}

// ---------------------------------------------------------------------------
//  Mesure AC — valeur efficace de la composante alternative, en mV.
//  Passe unique : variance = E[x²] - E[x]²  ->  RMS_AC = sqrt(variance).
//  analogReadMilliVolts() applique la calibration eFuse.
// ---------------------------------------------------------------------------
float readRmsMilliVolts(int pin) {
  const uint32_t start = micros();
  double sum = 0.0, sumSq = 0.0;
  uint32_t n = 0;

  while ((micros() - start) < (uint32_t)ADC_WINDOW_MS * 1000UL) {
    uint32_t mv = analogReadMilliVolts(pin);
    sum   += mv;
    sumSq += (double)mv * (double)mv;
    n++;
  }
  if (n == 0) return 0.0f;

  double mean = sum / n;
  double var  = (sumSq / n) - (mean * mean);
  if (var < 0) var = 0;
  return (float)sqrt(var);
}

float lineVoltage(int i) { return readRmsMilliVolts(vPins[i]) * V_SCALE[i]; } // Vrms secteur
float lineCurrent(int i) { return readRmsMilliVolts(iPins[i]) * I_SCALE[i]; } // Irms

// ---------------------------------------------------------------------------
//  HTTP — une primitive pour POST / GET / PATCH / PUT
// ---------------------------------------------------------------------------
String backendUrl(const char* path) {
  return String("http://") + BACKEND_HOST + ":" + String(BACKEND_PORT) + path;
}

int httpSend(const char* method, const String& url, const String& body, String& out) {
  if (WiFi.status() != WL_CONNECTED) return -1;

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);   // correctif d'authentification

  int code = http.sendRequest(method, body);
  if (code > 0) out = http.getString();
  http.end();
  return code;
}

// Applique une réponse texte "L1=1;L2=0;L3=1"
void applyServerRelayResponse(const String& body) {
  for (int i = 0; i < 3; i++) {
    String key = String(lineName(i)) + "=";
    int p = body.indexOf(key);
    if (p >= 0) {
      char c = body.charAt(p + key.length());
      if (c == '0' || c == '1') setLine(i, c == '1');
    }
  }
}

void postDecisionCycle() {
  float rawV[3], rawI[3], v[3], iA[3];
  for (int i = 0; i < 3; i++) {
    rawV[i] = readRmsMilliVolts(vPins[i]);   // mV efficaces bruts (utile calibration)
    rawI[i] = readRmsMilliVolts(iPins[i]);
    v[i]    = rawV[i] * V_SCALE[i];           // Vrms secteur
    iA[i]   = rawI[i] * I_SCALE[i];           // Irms
  }
  bool dcFresh = dcEver && (millis() - dcLastMs < DC_STALE_MS);

  // Corps attendu par EmsDecisionView : clés line1/line2/line3 (+ bloc dc).
  // La maison N'EST PAS envoyée : le backend la déduit du jeton d'appareil.
  // La puissance n'est pas envoyée : le backend calcule lui-même P = V x I.
  char body[640];
  int n = snprintf(body, sizeof(body),
    "{"
      "\"line1\":{\"voltage\":%.1f,\"current\":%.3f,\"vSensorRms\":%.1f,\"iSensorRms\":%.1f},"
      "\"line2\":{\"voltage\":%.1f,\"current\":%.3f,\"vSensorRms\":%.1f,\"iSensorRms\":%.1f},"
      "\"line3\":{\"voltage\":%.1f,\"current\":%.3f,\"vSensorRms\":%.1f,\"iSensorRms\":%.1f}",
    v[0], iA[0], rawV[0], rawI[0],
    v[1], iA[1], rawV[1], rawI[1],
    v[2], iA[2], rawV[2], rawI[2]);

  // Bloc DC (nœud secondaire), seulement s'il est frais. Le matériel a deux
  // batteries en parallèle mais le backend n'en modélise qu'une : on somme les
  // courants et on prend tension/température du parc. batteryCurrent est signé
  // (+ = charge).
  if (dcFresh && n > 0 && n < (int)sizeof(body)) {
    snprintf(body + n, sizeof(body) - n,
      ",\"dc\":{"
        "\"batteryVoltage\":%.2f,\"batteryCurrent\":%.3f,\"batteryTemp\":%.1f,"
        "\"pvVoltage\":%.2f,\"pvCurrent\":%.3f,\"panelTemp\":%.1f}}",
      dc.vBAT, dc.iBAT1 + dc.iBAT2, dc.tBAT1,
      dc.vPV, dc.iPV, dc.tPV);
  } else {
    strncat(body, "}", sizeof(body) - strlen(body) - 1);
  }

  String url = backendUrl(BACKEND_DECISION_PATH), resp;
  int code = httpSend("POST", url, String(body), resp);
  Serial.printf("[HTTP] POST %s -> %d (DC %s)\n", url.c_str(), code,
                dcFresh ? "frais" : "absent");

  if (code == 200 || code == 201) {
    Serial.printf("[HTTP] reponse : %s\n", resp.c_str());
#if APPLY_SERVER_RELAY_DECISION
    applyServerRelayResponse(resp);   // le backend renvoie "L1=..;L2=..;L3=.."
#endif
  } else if (code == 403) {
    Serial.printf("[HTTP] 403 (%s) — verifie DEVICE_TOKEN dans secrets.h\n", resp.c_str());
  }
}

// ---------------------------------------------------------------------------
//  Setup / Loop
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== EMS — Nœud PRINCIPAL (AC) ===");

  // Relais à l'état repos AVANT tout, pour limiter un collage au démarrage.
  for (int i = 0; i < 3; i++) {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], relayLevel(false));
    lineOn[i] = false;
  }

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  // UART2 vers le nœud secondaire (réception des mesures DC).
  Serial2.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);

  wifiEnsureConnected();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqttEnsureConnected();
}

void loop() {
  wifiEnsureConnected();
  mqttEnsureConnected();
  mqtt.loop();
  readUart();

#if HTTP_TELEMETRY_ENABLED
  static uint32_t lastPost = 0;
  if (millis() - lastPost >= POST_INTERVAL_MS) { lastPost = millis(); postDecisionCycle(); }
#endif
}