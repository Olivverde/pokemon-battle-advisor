import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier


def load_dataset(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    return df


def add_opponent_hp(df: pd.DataFrame) -> pd.DataFrame:
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


def evaluate(model: XGBClassifier, X_test: pd.DataFrame, y_test: pd.Series) -> None:
    y_pred = model.predict(X_test)
    f1_macro = f1_score(y_test, y_pred, average='macro')

    print(f"F1-macro: {f1_macro:.2f}\n")
    print("Classification report:")
    print(classification_report(y_test, y_pred, digits=4))
    print("Confusion matrix:")
    print(confusion_matrix(y_test, y_pred))


def save_artifacts(model: XGBClassifier, label_encoder: LabelEncoder, model_path: Path, encoder_path: Path) -> None:
    os.makedirs(model_path.parent, exist_ok=True)
    joblib.dump(model, model_path)
    joblib.dump(label_encoder, encoder_path)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dataset_path = repo_root / 'data' / 'processed' / 'battle_turns_enriched.csv'
    model_path = repo_root / 'models' / 'pokemon_advisor.joblib'
    encoder_path = repo_root / 'models' / 'label_encoder.joblib'

    print('Cargando dataset...')
    df = load_dataset(dataset_path)
    print(f'Dataset cargado: {df.shape[0]} filas, {df.shape[1]} columnas')

    X, y, target_encoder = prepare_features(df)
    X_train, X_test, y_train, y_test = temporal_split(X, y, df)

    print(f'Entrenando con {X_train.shape[0]} filas y evaluando con {X_test.shape[0]} filas')

    model = train_model(X_train, y_train)
    evaluate(model, X_test, y_test)

    save_artifacts(model, target_encoder, model_path, encoder_path)
    print(f'Modelo guardado en {model_path}')
    print(f'LabelEncoder guardado en {encoder_path}')


if __name__ == '__main__':
    main()
