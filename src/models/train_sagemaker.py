import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost==1.7.6"])

import os
import json

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# Variables de entorno de SageMaker
SM_MODEL_DIR = os.environ.get("SM_MODEL_DIR", "models/")
SM_CHANNEL_TRAIN = os.environ.get("SM_CHANNEL_TRAIN", "data/processed/")

print(f"📍 SM_CHANNEL_TRAIN: {SM_CHANNEL_TRAIN}")
print(f"📍 SM_MODEL_DIR: {SM_MODEL_DIR}")


def add_opponent_hp(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega HP del oponente con self-join"""
    opponent_hp = (
        df[['battle_id', 'turn', 'player', 'hp']]
        .copy()
        .rename(columns={'hp': 'hp_opp'})
    )
    opponent_hp['player'] = opponent_hp['player'].map({'p1': 'p2', 'p2': 'p1'})

    df = df.merge(
        opponent_hp[['battle_id', 'turn', 'player', 'hp_opp']],
        on=['battle_id', 'turn', 'player'],
        how='left',
    )
    df['hp_opp'] = df['hp_opp'].fillna(100.0)
    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, LabelEncoder]:
    """Prepara features y target para el modelo"""
    df = df.copy()

    df = add_opponent_hp(df)

    # Convertir booleanos a int para el modelo
    df['stealth_rock_own'] = df['stealth_rock_own'].astype(int)
    df['stealth_rock_opp'] = df['stealth_rock_opp'].astype(int)

    # Feature engineering mínima
    df['weather'] = df['weather'].fillna('none')
    df['terrain'] = df['terrain'].fillna('none')

    feature_columns = [
        'hp',
        'hp_opp',
        'spikes_own',
        'spikes_opp',
        'stealth_rock_own',
        'stealth_rock_opp',
        'weather',
        'terrain',
        'active_pokemon',
    ]

    X = df[feature_columns].copy()

    # One-hot encode weather/terrain
    X = pd.get_dummies(X, columns=['weather', 'terrain'], dummy_na=False)

    # Label encode active_pokemon
    pokemon_encoder = LabelEncoder()
    X['active_pokemon'] = pokemon_encoder.fit_transform(X['active_pokemon'].astype(str))

    # Target
    target_encoder = LabelEncoder()
    y = pd.Series(target_encoder.fit_transform(df['action'].astype(str)), index=df.index)

    return X, y, target_encoder


def temporal_split(X: pd.DataFrame, y: pd.Series, df: pd.DataFrame, train_ratio: float = 0.8) -> tuple:
    """Split temporal sin aleatorización para evitar data leakage"""
    sorted_idx = df.sort_values(['battle_id', 'turn']).index
    X = X.loc[sorted_idx].reset_index(drop=True)
    y = y[sorted_idx].reset_index(drop=True)

    split_index = int(len(X) * train_ratio)
    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]
    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> XGBClassifier:
    """Entrena el modelo XGBoost"""
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def evaluate(model: XGBClassifier, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """Evalúa el modelo y retorna métricas"""
    y_pred = model.predict(X_test)
    f1_macro = f1_score(y_test, y_pred, average='macro')

    print(f"F1-macro: {f1_macro:.2f}\n")
    print("Classification report:")
    print(classification_report(y_test, y_pred, digits=4))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    return {"f1_macro": f1_macro}


def main():
    # Construir ruta del dataset
    data_path = os.path.join(SM_CHANNEL_TRAIN, "battle_turns_enriched.csv")
    print(f"🔄 Cargando dataset desde: {data_path}")

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset no encontrado: {data_path}")

    df = pd.read_csv(data_path)
    print(f"📊 Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas")

    # Preparar features
    X, y, target_encoder = prepare_features(df)
    X_train, X_test, y_train, y_test = temporal_split(X, y, df)

    print(f"📈 Train: {X_train.shape[0]} filas, Test: {X_test.shape[0]} filas")

    # Entrenar modelo
    print("🎯 Entrenando modelo XGBoost...")
    model = train_model(X_train, y_train)

    # Evaluar
    print("\n📊 Evaluando modelo...")
    metrics = evaluate(model, X_test, y_test)

    # Guardar artefactos
    os.makedirs(SM_MODEL_DIR, exist_ok=True)

    model_path = os.path.join(SM_MODEL_DIR, "pokemon_advisor.joblib")
    encoder_path = os.path.join(SM_MODEL_DIR, "label_encoder.joblib")

    joblib.dump(model, model_path)
    joblib.dump(target_encoder, encoder_path)

    print(f"\n✅ Modelo guardado en {model_path}")
    print(f"✅ LabelEncoder guardado en {encoder_path}")

    # Guardar métricas
    metrics_path = os.path.join(SM_MODEL_DIR, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f)

    print(f"✅ Métricas guardadas en {metrics_path}")


if __name__ == "__main__":
    main()
