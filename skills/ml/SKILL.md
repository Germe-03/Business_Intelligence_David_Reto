# SKILL: ML – Runway-Vorhersage

## Trigger
Wenn ein ML-Modell trainiert, evaluiert oder für das Dashboard verwendet wird.

## Ziel
Input: Wetterbedingungen + Flugzeugkategorie → Output: empfohlene Piste (RWY)

## Features
- `wind` (Geschwindigkeit), `winddirection` (0–360°)
- `weather` (Label-encoded: Nebel, Regen, Schnee, etc.)
- `temp`, `humidity`
- `aircraft_category` (Klein/Mittel/Gross aus TYS)
- `is_arrival` (0/1)

## Training
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))
joblib.dump(model, "models/runway_classifier.pkl")
```

## Laden im Dashboard
```python
model = joblib.load("models/runway_classifier.pkl")
prediction = model.predict([[wind, direction, weather_enc, temp, humidity, category, is_arrival]])
probabilities = model.predict_proba(...)
```

## Modelle speichern unter
`models/runway_classifier.pkl` (gitignored, separat teilen)
