#define RELAY_L1 25   // G25 -> IN1
#define RELAY_L2 26   // G26 -> IN3
#define RELAY_L3 27   // G27 -> IN6

// Beaucoup de modules relais sont actifs à LOW.
// Si tes relais fonctionnent à l'envers, inverse RELAY_ON et RELAY_OFF.
#define RELAY_ON  LOW
#define RELAY_OFF HIGH

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_L1, OUTPUT);
  pinMode(RELAY_L2, OUTPUT);
  pinMode(RELAY_L3, OUTPUT);

  digitalWrite(RELAY_L1, RELAY_OFF);
  digitalWrite(RELAY_L2, RELAY_OFF);
  digitalWrite(RELAY_L3, RELAY_OFF);

  Serial.println("Test relais ESP32 - CH1, CH3, CH6");
}

void loop() {
  Serial.println("Ligne 1 ON");
  digitalWrite(RELAY_L1, RELAY_ON);
  delay(2000);
  digitalWrite(RELAY_L1, RELAY_OFF);
  Serial.println("Ligne 1 OFF");
  delay(1000);

  Serial.println("Ligne 2 ON");
  digitalWrite(RELAY_L2, RELAY_ON);
  delay(2000);
  digitalWrite(RELAY_L2, RELAY_OFF);
  Serial.println("Ligne 2 OFF");
  delay(1000);

  Serial.println("Ligne 3 ON");
  digitalWrite(RELAY_L3, RELAY_ON);
  delay(2000);
  digitalWrite(RELAY_L3, RELAY_OFF);
  Serial.println("Ligne 3 OFF");
  delay(3000);
}
