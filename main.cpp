#include <Arduino.h>
#include <AccelStepper.h>

#define DIR_PIN 27
#define STEP_PIN 26

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

const int STEPS_PER_REV = 200; // 1.8°/step
int microstep = 1;             // déjalo en 1 por ahora
long home_steps = 0;           // "0 grados" en pasos

long degToSteps(float deg) {
  return lround((deg / 360.0f) * (STEPS_PER_REV * microstep));
}

String line;

void setup() {
  Serial.begin(115200);
  stepper.setMaxSpeed(400);
  stepper.setAcceleration(200);

  Serial.println("Comandos:");
  Serial.println("  HOME");
  Serial.println("  GOTO <deg>   (ej: GOTO 90)");
  Serial.println("  MOVE <steps> (ej: MOVE -200)");
  Serial.println("  POS?");
}

void handleCmd(String cmd) {
  cmd.trim();

  String up = cmd; up.toUpperCase();

  if (up == "HOME") {
    home_steps = stepper.currentPosition();
    Serial.println("OK HOME -> aqui es 0 deg");
    return;
  }

  if (up.startsWith("GOTO ")) {
    float deg = cmd.substring(5).toFloat();           // usa cmd original por si hay '-' o decimales
    long target = home_steps + degToSteps(deg);
    stepper.moveTo(target);
    Serial.print("OK GOTO "); Serial.print(deg);
    Serial.print(" deg -> target steps "); Serial.println(target);
    return;
  }

  if (up.startsWith("MOVE ")) {
    long s = cmd.substring(5).toInt();
    stepper.move(s);
    Serial.print("OK MOVE "); Serial.println(s);
    return;
  }

  if (up == "POS?") {
    long cur = stepper.currentPosition();
    Serial.print("steps="); Serial.print(cur);
    Serial.print("  rel_from_home="); Serial.println(cur - home_steps);
    return;
  }

  Serial.println("ERR. Usa: HOME | GOTO <deg> | MOVE <steps> | POS?");
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') { handleCmd(line); line = ""; }
    else if (c != '\r') line += c;
  }
  stepper.run();
}   