# Skill: ML-Vorhersagen

## Zweck
Vorhersagemodelle für das Flughafen-Dashboard trainieren und integrieren.

## Vorhersage 1: Flugverspätung (Klassifikation)
**Ziel:** Wird ein Flug verspätet? (ja/nein)
**Features:** Wochentag, Uhrzeit, Airline, Route, Wetter (Temp, Wind, Wetterlage)
**Label:** `delay = 1` wenn `departure_new > departure_old` in flight_log

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

X = df[['weekday', 'hour', 'airline_id', 'from', 'to', 'temp', 'wind', 'weather_encoded']]
y = df['is_delayed']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))
```

## Vorhersage 2: Buchungsauslastung (Regression)
**Ziel:** Wie voll wird ein Flug? (0–100%)
**Features:** Route, Wochentag, Airline, Flugzeugtyp, Abflugzeit
**Label:** `occupancy_pct = bookings / capacity * 100`

```python
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

model = GradientBoostingRegressor()
model.fit(X_train, y_train)
print("MAE:", mean_absolute_error(y_test, model.predict(X_test)))
```

## Modelle speichern & laden
```python
import joblib

# Speichern
joblib.dump(model, "models/delay_classifier.pkl")

# Laden (für Dashboard)
model = joblib.load("models/delay_classifier.pkl")
```

## Feature Engineering
- `weekday`: `departure.dt.dayofweek`
- `hour`: `departure.dt.hour`
- `weather_encoded`: LabelEncoder auf `weatherdata.weather`
- `route`: Kombination aus `from` + `to` Airport-IDs
- `delay_minutes`: `TIMESTAMPDIFF(MINUTE, departure_old, departure_new)`

## Modell-Evaluation Output
Für jedes Modell speichern:
- Metriken: `models/metrics_{modellname}.json`
- Feature Importance Plot
- Confusion Matrix (Klassifikation) / Residual Plot (Regression)
