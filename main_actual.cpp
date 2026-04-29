#include <Arduino.h>
#include <AccelStepper.h>
#include <math.h>

#define DIR_PIN 4
#define STEP_PIN 5

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

// CONFIG
const int STEPS_PER_REV = 200;
int microstep = 1;
const float STEPS_TOTAL = STEPS_PER_REV * microstep;

long home_steps = 0;

String line;

// =====================
// CONVERSIONES
// =====================

long degToSteps(float deg) {
  return lround((deg / 360.0f) * STEPS_TOTAL);
}

float stepsToDeg(long steps) {
  return (steps * 360.0f) / STEPS_TOTAL;
}

// =====================
// SHORTEST PATH
// =====================

float shortest_delta(float current, float target) {
  float delta = fmod((target - current), 360.0);

  if (delta > 180.0) delta -= 360.0;
  if (delta < -180.0) delta += 360.0;

  return delta;
}

// =====================
// SETUP
// =====================

void setup() {
  Serial.begin(115200);

  stepper.setMaxSpeed(1500);
  stepper.setAcceleration(800);

  Serial.println("READY");
}

// =====================
// GOTO (CLAVE)
// =====================

void handleGoto(String cmd) {
  float target_deg = cmd.substring(5).toFloat();

  long current_steps = stepper.currentPosition() - home_steps;
  float current_deg = stepsToDeg(current_steps);

  float delta_deg = shortest_delta(current_deg, target_deg);
  long steps = degToSteps(delta_deg);

  stepper.move(steps);
}

// =====================
// COMANDOS
// =====================

void handleCmd(String cmd) {
  cmd.trim();

  String up = cmd;
  up.toUpperCase();

  if (up == "HOME") {
    home_steps = stepper.currentPosition();
    Serial.println("OK HOME");
    return;
  }

  if (up.startsWith("GOTO ")) {
    handleGoto(cmd);
    return;
  }

  if (up == "RESET") {
    home_steps = 0;  //volver al cero absoluto
    Serial.println("OK RESET");
    return;
}
}

// =====================
// LOOP
// =====================

void loop() {

  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      handleCmd(line);
      line = "";
    } else {
      line += c;
    }
  }

  stepper.run();
}
