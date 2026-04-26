/*
  Circuit-Sensei Arduino tester

  Serial protocol: send one JSON-like command per line at 115200 baud.
  Example: {"cmd":"READ_ANALOG","pin":"A0"}

  This sketch intentionally avoids third-party Arduino JSON libraries. It uses
  a small permissive parser that is enough for the command shapes emitted by the
  Python prototype.
*/

const float ADC_REF_VOLTS = 5.0;

String readLine() {
  String line = Serial.readStringUntil('\n');
  line.trim();
  return line;
}

String getStringValue(const String &line, const String &key, const String &fallback = "") {
  String needle = "\"" + key + "\"";
  int keyPos = line.indexOf(needle);
  if (keyPos < 0) {
    return fallback;
  }
  int colon = line.indexOf(':', keyPos);
  if (colon < 0) {
    return fallback;
  }
  int firstQuote = line.indexOf('"', colon + 1);
  if (firstQuote < 0) {
    return fallback;
  }
  int secondQuote = line.indexOf('"', firstQuote + 1);
  if (secondQuote < 0) {
    return fallback;
  }
  return line.substring(firstQuote + 1, secondQuote);
}

long getNumberValue(const String &line, const String &key, long fallback = 0) {
  String needle = "\"" + key + "\"";
  int keyPos = line.indexOf(needle);
  if (keyPos < 0) {
    return fallback;
  }
  int colon = line.indexOf(':', keyPos);
  if (colon < 0) {
    return fallback;
  }
  int start = colon + 1;
  while (start < line.length() && (line[start] == ' ' || line[start] == '"')) {
    start++;
  }
  int end = start;
  while (end < line.length() && (isDigit(line[end]) || line[end] == '-' || line[end] == '.')) {
    end++;
  }
  return line.substring(start, end).toInt();
}

int parsePin(const String &pin) {
  if (pin.length() >= 2 && (pin[0] == 'A' || pin[0] == 'a')) {
    int analogIndex = pin.substring(1).toInt();
    return A0 + analogIndex;
  }
  return pin.toInt();
}

void respondOkValue(float value, const String &unit) {
  Serial.print("{\"status\":\"ok\",\"value\":");
  Serial.print(value, 3);
  Serial.print(",\"unit\":\"");
  Serial.print(unit);
  Serial.println("\"}");
}

void respondOkInt(int value) {
  Serial.print("{\"status\":\"ok\",\"value\":");
  Serial.print(value);
  Serial.println("}");
}

void respondStatus(const String &status, const String &message = "") {
  Serial.print("{\"status\":\"");
  Serial.print(status);
  Serial.print("\"");
  if (message.length() > 0) {
    Serial.print(",\"message\":\"");
    Serial.print(message);
    Serial.print("\"");
  }
  Serial.println("}");
}

void runVoltageDividerTest(const String &line) {
  String pinName = getStringValue(line, "pin", "A0");
  int pin = parsePin(pinName);
  int raw = analogRead(pin);
  float volts = raw * ADC_REF_VOLTS / 1023.0;
  Serial.print("{\"status\":\"ok\",\"test_type\":\"voltage_divider\",\"measurements\":{\"");
  Serial.print(pinName);
  Serial.print("\":");
  Serial.print(volts, 3);
  Serial.println("}}");
}

void runLedTest(const String &line) {
  int drivePin = getNumberValue(line, "drive_pin", 9);
  String sensePinName = getStringValue(line, "sense_pin", "A0");
  int sensePin = parsePin(sensePinName);
  pinMode(drivePin, OUTPUT);
  digitalWrite(drivePin, HIGH);
  delay(100);
  float volts = analogRead(sensePin) * ADC_REF_VOLTS / 1023.0;
  digitalWrite(drivePin, LOW);
  Serial.print("{\"status\":\"ok\",\"test_type\":\"led\",\"measurements\":{\"sense_voltage\":");
  Serial.print(volts, 3);
  Serial.println("}}");
}

void runButtonTest(const String &line) {
  int pin = getNumberValue(line, "pin", 2);
  pinMode(pin, INPUT_PULLUP);
  delay(20);
  int value = digitalRead(pin);
  Serial.print("{\"status\":\"ok\",\"test_type\":\"button\",\"measurements\":{\"digital\":");
  Serial.print(value);
  Serial.println("}}");
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(2000);
  respondStatus("ok", "Circuit-Sensei tester ready");
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  String line = readLine();
  if (line.length() == 0) {
    return;
  }

  String cmd = getStringValue(line, "cmd");
  cmd.toUpperCase();

  if (cmd == "SET_DIGITAL") {
    int pin = getNumberValue(line, "pin");
    int value = getNumberValue(line, "value");
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value ? HIGH : LOW);
    respondStatus("ok");
  } else if (cmd == "SET_PWM") {
    int pin = getNumberValue(line, "pin");
    int value = constrain(getNumberValue(line, "value"), 0, 255);
    pinMode(pin, OUTPUT);
    analogWrite(pin, value);
    respondStatus("ok");
  } else if (cmd == "READ_DIGITAL") {
    int pin = getNumberValue(line, "pin");
    pinMode(pin, INPUT);
    respondOkInt(digitalRead(pin));
  } else if (cmd == "READ_ANALOG") {
    int pin = A0 + (int)getNumberValue(line, "pin", 0);
    float volts = analogRead(pin) * ADC_REF_VOLTS / 1023.0;
    respondOkValue(volts, "V");
  } else if (cmd == "RUN_TEST") {
    String testType = getStringValue(line, "test_type", "generic");
    testType.toLowerCase();
    if (testType == "voltage_divider") {
      runVoltageDividerTest(line);
    } else if (testType == "led") {
      runLedTest(line);
    } else if (testType == "button") {
      runButtonTest(line);
    } else {
      runVoltageDividerTest(line);
    }
  } else {
    respondStatus("error", "unsupported command");
  }
}
