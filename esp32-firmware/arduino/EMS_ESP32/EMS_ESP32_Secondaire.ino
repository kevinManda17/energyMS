// ============================================================================
//  EMS IoT — Nœud SECONDAIRE (DC)
//  ----------------------------------------------------------------------------
//  Rôle : mesurer 3 courants (ACS712), 3 tensions (ponts diviseurs) et
//         3 températures (NTC), puis envoyer le tout par UART au nœud principal.
//  Réseau : AUCUN. Le WiFi est coupé, c'est ce qui rend l'ADC2 utilisable pour
//           les voies NTC.
//
//  Cible   : ESP32 WROOM-32 (carte "ESP32 Dev Module").
//  Dépend. : aucune bibliothèque externe.
//
//  Dossier de sketch : EMS_ESP32_Secondaire/  contenant config_secondaire.h.
// ============================================================================

#include <math.h>
#include "config_secondaire.h"

const int iPins[3] = { PIN_I_DC1, PIN_I_DC2, PIN_I_DC3 };
const int vPins[3] = { PIN_V_DC1, PIN_V_DC2, PIN_V_DC3 };
const int tPins[3] = { PIN_T_1,   PIN_T_2,   PIN_T_3   };

// ---------------------------------------------------------------------------
//  Acquisition — moyenne de N échantillons calibrés (mV), espacés de 1 ms.
// ---------------------------------------------------------------------------
float avgMilliVolts(int pin) {
  double sum = 0.0;
  for (int k = 0; k < DC_SAMPLES; k++) {
    sum += analogReadMilliVolts(pin);
    delay(DC_GAP_MS);
  }
  return (float)(sum / DC_SAMPLES);
}

// Courant ACS712 : on retire le zéro, on annule le pont, on divise par la sensibilité.
float readCurrent(int ch) {
  float mv   = avgMilliVolts(iPins[ch]);
  float vacs = (mv - ACS_VZERO_MV[ch]) / 1000.0f / ACS_KDIV;   // V côté ACS712
  return vacs / ACS_SENS[ch];                                  // A
}

// Tension DC : simple facteur d'échelle (pont 100k/15k + étalonnage).
float readVoltage(int ch) {
  return avgMilliVolts(vPins[ch]) * VDC_SCALE[ch];             // V
}

// Température NTC : loi Beta. Renvoie NTC_INVALID si hors plage.
float readTemperature(int ch) {
  float v = avgMilliVolts(tPins[ch]) / 1000.0f;                // V
  if (v <= 0.0f || v >= NTC_VSUP) return NTC_INVALID;
  float r    = NTC_RFIXED * v / (NTC_VSUP - v);                // Ohm
  float invT = 1.0f / NTC_T0_K + logf(r / NTC_R0) / NTC_BETA;
  return 1.0f / invT - 273.15f;                                // °C
}

// ---------------------------------------------------------------------------
//  Envoi UART — trame $DC,...*CK\n  (CK = XOR hex entre '$' et '*').
//  LE FORMAT DOIT ÊTRE IDENTIQUE côté principal.
// ---------------------------------------------------------------------------
void sendFrame(float i1, float i2, float i3,
               float v1, float v2, float v3,
               float t1, float t2, float t3) {
  char payload[128];
  snprintf(payload, sizeof(payload),
           "DC,%.3f,%.3f,%.3f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f",
           i1, i2, i3, v1, v2, v3, t1, t2, t3);

  uint8_t ck = 0;
  for (char* p = payload; *p; p++) ck ^= (uint8_t)*p;

  Serial2.printf("$%s*%02X\n", payload, ck);   // vers le nœud principal
  Serial.printf("[DC] $%s*%02X\n", payload, ck); // écho debug USB
}

// ---------------------------------------------------------------------------
//  Setup / Loop
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== EMS — Nœud SECONDAIRE (DC) ===");

  // Pas de WiFi : indispensable pour garder l'ADC2 (voies NTC).
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  // UART2 vers le nœud principal.
  Serial2.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < SEND_INTERVAL_MS) return;
  last = millis();

  float i1 = readCurrent(0), i2 = readCurrent(1), i3 = readCurrent(2);
  float v1 = readVoltage(0), v2 = readVoltage(1), v3 = readVoltage(2);
  float t1 = readTemperature(0), t2 = readTemperature(1), t3 = readTemperature(2);

  sendFrame(i1, i2, i3, v1, v2, v3, t1, t2, t3);
}
