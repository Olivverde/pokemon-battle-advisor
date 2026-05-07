# Pokémon Battle Advisor 🔥

Sistema MLOps end-to-end para análisis y predicción de acciones óptimas en batallas competitivas de Pokémon Showdown.

## Descripción del Proyecto

**Pokémon Battle Advisor** es un proyecto de portafolio que demuestra capacidades en:
- **Data Engineering**: Ingesta de datos en tiempo real desde APIs
- **Machine Learning**: Clasificación de acciones óptimas
- **Cloud Deployment**: Despliegue serverless en AWS
- **MLOps**: Pipeline completo de datos a producción

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│  Data Ingestion                                         │
│  - Pokémon Showdown API                                │
│  - Descarga de logs de batallas                        │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Data Processing                                        │
│  - Parsing de logs                                     │
│  - Feature engineering                                 │
│  - Preprocesamiento                                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Model Training                                         │
│  - Clasificación (Random Forest / XGBoost)            │
│  - Hyperparameter tuning                               │
│  - Cross-validation                                    │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  API Serverless (AWS Lambda + API Gateway)            │
│  - Inferencia en tiempo real                           │
│  - Predicción de acciones óptimas                      │
└─────────────────────────────────────────────────────────┘
```

## Estructura del Proyecto

```
pokemon_advisor/
├── data/                          # Datos
│   ├── raw/                       # Logs descargados
│   ├── processed/                 # Datos procesados
│   └── splits/                    # Train/Val/Test
├── notebooks/                     # Experimentación
│   ├── 01_eda.ipynb
│   └── 02_feature_engineering.ipynb
├── src/                           # Código principal
│   ├── pipeline/                  # Ingesta y procesamiento
│   │   ├── fetch.py               # Descarga desde API
│   │   ├── parser.py              # Parsing de logs
│   │   └── preprocessor.py        # Preprocesamiento
│   ├── models/                    # Modelos
│   │   ├── trainer.py             # Entrenamiento
│   │   └── inference.py           # Inferencia
│   └── utils/                     # Utilidades
│       └── config.py
├── api/                           # API
│   ├── app.py                     # FastAPI app
│   └── lambda_handler.py          # AWS Lambda
├── models/                        # Modelos entrenados
├── tests/                         # Tests
│   ├── test_pipeline.py
│   └── test_models.py
├── config/                        # Configuración
│   └── config.json
├── deployment/                    # Deployment
├── requirements.txt               # Dependencias
├── .gitignore
└── README.md
```

## Requisitos

- Python 3.9+
- pip o conda

## Instalación

1. **Clonar el repositorio**
```bash
git clone <repo-url>
cd pokemon_advisor
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

## Uso

### 1. Descargar datos
```python
from src.pipeline import save_replays

# Descargar 500 replays de formato gen9ou
save_replays("gen9ou", n=500)
```

### 2. Preprocesar datos
```python
# TODO: Implementar
```

### 3. Entrenar modelo
```python
# TODO: Implementar
```

### 4. Ejecutar API
```bash
uvicorn api.app:app --reload
```

## Development

### Ejecutar tests
```bash
pytest tests/ -v --cov=src
```

### Formatear código
```bash
black src/ tests/
```

### Linting
```bash
flake8 src/ tests/
```

## Notas Importantes

- El parsing es todavía un **TODO** - necesita completarse
- El modelo de inferencia es un **stub** - agregar lógica de predicción
- La API Lambda necesita testing en AWS

## Roadmap

- [ ] Completar parser de logs
- [ ] Implementar feature engineering
- [ ] Entrenar modelos baseline
- [ ] CI/CD con GitHub Actions
- [ ] Despliegue en AWS Lambda
- [ ] Dashboard de monitoreo
- [ ] Versionado de modelos (MLflow)

## Licencia

MIT

## Autor

Oliver
