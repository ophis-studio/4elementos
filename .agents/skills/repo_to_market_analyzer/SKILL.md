---
name: repo_to_market_analyzer
description: >-
  Audita un repositorio de software, identifica competidores/papers científicos del estado del arte, y estructura una estrategia de negocios/monetización (Lean Canvas y modelo financiero).
---

# Auditor Estratégico de Repositorio y Negocio (`repo_to_market_analyzer`)

## Overview
Esta skill faculta al agente para realizar una auditoría integral de tres dimensiones de cualquier proyecto de software:
1. **Inspección Técnica de Código (SAST, SCA, AST):** Análisis estático para determinar el stack tecnológico, dependencias, licencias, calidad de código, nivel de pruebas y deuda técnica.
2. **Investigación del Estado del Arte y Mercado:** Búsqueda activa de competidores open-source y comerciales, papers académicos recientes y la brecha tecnológica del proyecto.
3. **Arquitectura y Estrategia de Negocio:** Diseño de una propuesta de monetización (SaaS, Open-Core, Dual-Licensing, etc.), Lean Canvas y estimación financiera de un MVP.

## Dependencies
- **Python 3.10+** (utiliza únicamente la biblioteca estándar de Python: `urllib`, `json`, `ast`, `argparse`, `sys`, `pathlib`).
- Opcional: **Git CLI** (para análisis de repositorios remotos clonados temporalmente).

## Quick Start
Ejecuta la auditoría en orden secuencial usando el script de utilidad CLI:

```bash
# Paso 1: Analizar el código local
python repo_to_market_analyzer.py inspect-code --repo-path "C:/ruta/al/proyecto" --output inspect.json

# Paso 2: Investigar el mercado y estado del arte
python repo_to_market_analyzer.py research-market --query "monitoreo porcino iot" --tech-stack "python, html, vanilla css" --output market.json

# Paso 3: Generar la propuesta de negocio y matriz financiera
python repo_to_market_analyzer.py business-architect --audit-results inspect.json --market-results market.json --monetization-pattern "SaaS" --output business.json
```

## Utility Scripts

El script CLI principal se encuentra en `.agents/skills/repo_to_market_analyzer/repo_to_market_analyzer.py`.

### 1. `inspect-code`
- **Descripción:** Escanea recursivamente un directorio local, lee archivos clave (`package.json`, `requirements.txt`, etc.), y realiza análisis estático AST sobre archivos Python y Javascript.
- **Argumentos obligatorios:**
  - `--repo-path`: Ruta absoluta del directorio a inspeccionar.
  - `--output`: Ruta del archivo JSON donde se guardarán los resultados del análisis.
- **Campos del JSON resultante:** `files_count`, `extensions`, `dependencies`, `licenses_detected`, `test_coverage_est`, `tech_debt_score` (basado en TODOs/FIXMEs y llamadas de riesgo), `architecture_patterns`.

### 2. `research-market`
- **Descripción:** Busca proyectos alternativos y competidores directos en la API de GitHub, y busca papers científicos indexados en arXiv y OpenAlex relacionados con el stack tecnológico y área temática del repositorio.
- **Argumentos obligatorios:**
  - `--query`: Términos de búsqueda del dominio del proyecto (ej. "engorde porcino", "simulador financiero").
  - `--tech-stack`: Tecnologías principales del proyecto separadas por comas.
  - `--output`: Ruta del archivo JSON de salida.

### 3. `business-architect`
- **Descripción:** Traduce las fortalezas técnicas de la inspección y las oportunidades del mercado en una matriz Lean Canvas completa y proyecciones de rentabilidad/costos del MVP.
- **Argumentos obligatorios:**
  - `--audit-results`: Archivo JSON generado por `inspect-code`.
  - `--market-results`: Archivo JSON generado por `research-market`.
  - `--monetization-pattern`: Modelo propuesto (`SaaS`, `Open-Core`, `API-First`, `Self-Hosted`, `Dual-License`, `Auto`).
  - `--output`: Ruta del archivo JSON de salida.

## Workflow para el Agente

Cuando ejecutes esta skill de forma manual:
1. **Analiza el código:** Inicia con `inspect-code` para comprender qué lenguajes predominan, qué librerías se usan y la complejidad de la arquitectura.
2. **Revisa las licencias:** Pon especial atención a licencias restrictivas (como GPL) que limiten el empaquetado privativo, sugiriendo patrones de monetización como *Open-Core* o *Dual-Licensing*.
3. **Investiga papers y competidores:** Utiliza `research-market`. Busca comprender qué valor añadido técnico tiene este repositorio que los competidores no tengan.
4. **Construye el modelo financiero y Lean Canvas:** Usa `business-architect` para cuantificar los costos operativos iniciales (desarrolladores, infraestructura) y proyectar ingresos a partir de planes básico, profesional y empresarial configurables.

## Rate Limiting
- **GitHub API:** La API pública de GitHub tiene un límite de 60 peticiones por hora para llamadas no autenticadas. El script incluye un delay preventivo y reintentos automáticos con retroceso exponencial.
- **OpenAlex & arXiv APIs:** Límite preventivo de 1 petición por segundo para respetar los términos de uso.

## Common Mistakes
1. **Rutas inexistentes:** Pasar una ruta de `--repo-path` relativa o inexistente. Utiliza siempre rutas absolutas.
2. **Conflictos de formato de JSON:** Asegúrate de que los archivos de entrada para `business-architect` correspondan exactamente a los archivos JSON válidos generados en los pasos anteriores.
