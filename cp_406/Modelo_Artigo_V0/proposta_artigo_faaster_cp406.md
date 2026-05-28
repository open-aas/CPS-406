# Proposta de Artigo — Faaster + CPS-406

> **Status:** Rascunho de proposta  
> **Branch:** artigo  
> **Data:** 2026-05-28

---

## Título Principal (recomendado)

**"AAS-Driven Digital Twins for Modular Manufacturing: Automated OPC UA Runtime Generation from Asset Administration Shell V3 Models Applied to the Festo CP-406 Production System"**

### Títulos Alternativos

- *"From Static AAS V3 Models to Live OPC UA Servers: The Faaster Framework Applied to a Seven-Station Modular Manufacturing Plant"*
- *"Per-Module Digital Twin Generation Using Asset Administration Shell V3 and Faaster: A Case Study on the Festo CP-406 Didactic Factory"*
- *"Interoperable Digital Twins for Industry 4.0: Automated AAS V3 to OPC UA Mapping via Faaster on the CP-406 Cyber-Physical Production System"*

---

## Abstract (rascunho)

Digital twins (DTs) are a cornerstone of Industry 4.0, enabling real-time monitoring, simulation, and decision support in manufacturing systems. However, existing DT implementations often rely on proprietary platforms, lack standardized data models, and fail to provide per-module granularity in modular production environments. This paper presents a standards-based framework for automated DT generation applied to the Festo CP-406 modular manufacturing system, comprising seven heterogeneous stations including a Universal Robots UR5e collaborative robot. Each physical module is modeled as a standalone Asset Administration Shell (AAS) V3 compliant JSON document, encompassing eight submodels per station: Nameplate, TechnicalData, Documentation, IOInterface, and ProductionOrder for both the linear conveyor and the application module. The Faaster runtime automatically parses these AAS V3 documents and exposes a fully reactive OPC UA Type 2 server per station, with Historical Data Access (HDA) backed by TimescaleDB. Experimental evaluation demonstrates synchronization latency below X ms (p95), model fidelity above Y%, and linear scalability up to seven simultaneous OPC UA servers. Maturity assessment using RAMI 4.0 smart factory criteria shows improvements from Level Z (legacy) to Level W (updated) across all five criteria. The complete AAS model set and Faaster runtime are made available as open-source artifacts, enabling reproducibility and reuse across similar modular manufacturing environments.

**Keywords:** Asset Administration Shell, Digital Twin, OPC UA, Industry 4.0, RAMI 4.0, Modular Manufacturing, Faaster, Cyber-Physical System, Interoperability, Historical Data Access

---

## 1. Introdução

### 1.1 Motivação

A manufatura modular representa um paradigma crescente na Indústria 4.0, onde sistemas de produção são compostos por unidades autônomas e interoperáveis que podem ser reconfiguradas de acordo com demandas específicas. A planta **Festo CP-406** (CP-L-406-1) exemplifica este paradigma: sete estações heterogêneas — magazine de entrada, medição, furadeira, magazine de saída, prensa, saída e robô colaborativo UR5e — integradas em linha com esteiras lineares, PLCs Siemens ET200SP e comunicação RFID.

A criação de gêmeos digitais para tais sistemas enfrenta três desafios fundamentais:

1. **Fragmentação de padrões:** Ferramentas proprietárias (CIROS/Festo, Siemens NX Digital Twin, Dassault 3DExperience) criam modelos fechados, não interoperáveis entre si nem com outros sistemas I4.0.
2. **Granularidade inadequada:** Abordagens monolíticas modelam a planta como um bloco único, impedindo monitoramento e manutenção independentes por módulo.
3. **Lacuna entre especificação e execução:** O padrão AAS V3 (IEC 63278) define a estrutura do modelo, mas não provê mecanismo nativo de execução como servidor OPC UA vivo.

### 1.2 Lacuna na Literatura

Uma revisão da literatura recente (2020–2025) revela que:

- Trabalhos sobre AAS raramente demonstram integração OPC UA funcional em sistemas modulares completos
- Implementações de DT para manufatura usam predominantemente ferramentas proprietárias
- Nenhum trabalho identificado modela individualmente cada módulo de uma planta de 7 estações com AAS V3 padronizado e expõe via OPC UA com HDA
- O cobot UR5e é raramente tratado como estação AAS modelada em conjunto com PLCs industriais

### 1.3 Contribuições

Este artigo contribui com:

1. **Modelo AAS V3 completo e validado** para cada um dos 7 módulos do CPS-406, totalizando 8 submodelos por estação e 56 submodelos no total
2. **Faaster como runtime genérico** AAS V3 → OPC UA Type 2, com mapeamento automático de tipos (Property → Variable, Collection → Object, Operation → Method)
3. **Patch de validação PathType** para suporte a URLs HTTPS em thumbnails e documentação
4. **Avaliação quantitativa** de latência, fidelidade, escalabilidade e OEE com DT vs. sem DT
5. **Dataset público** da série temporal de sensores do CPS-406 via TimescaleDB/Zenodo
6. **Repositório aberto** (github.com/open-aas/CPS-406) com todos os artefatos reprodutíveis

---

## 2. Background e Trabalhos Relacionados

### 2.1 Asset Administration Shell (AAS) V3

O AAS é o modelo de dados central do paradigma I4.0 definido pela Platform Industrie 4.0 e padronizado como **IEC 63278**. A versão 3 (V3) introduz:

- **Tipos de SME:** Property, MultiLanguageProperty, File, Blob, ReferenceElement, SubmodelElementCollection, SubmodelElementList, Operation, AnnotatedRelationshipElement
- **Semantic IDs:** identificadores IRI ou IRDI (ECLASS) para semântica interoperável
- **PathType:** validação de caminhos para arquivos e URLs de documentação
- **Qualifiers e Extensions:** metadados adicionais por elemento

No CPS-406, os submodelos utilizam semantic IDs padronizados:
- IOInterface: `https://admin-shell.io/idta/IOInterface/1/0`
- ProductionOrder: `https://admin-shell.io/idta/ProductionOrder/1/0`

### 2.2 OPC UA como Protocolo de Integração I4.0

O **OPC UA (IEC 62541)** é o protocolo de comunicação de referência para I4.0. Distinguem-se dois tipos de servidores:

| Tipo | Característica | Aplicação |
|---|---|---|
| **Type 1 (Passive)** | Servidor expõe dados; clientes fazem poll | Sistemas legados, SCADA |
| **Type 2 (Reactive)** | Servidor publica mudanças; clientes subscrevem | DT em tempo real (Faaster) |

O Faaster implementa um servidor **Type 2** via `asyncua` (Python), garantindo que cada mudança no estado físico seja propagada automaticamente para todos os assinantes.

### 2.3 Comparação com Ferramentas Existentes

| Ferramenta | AAS V3 | OPC UA Nativo | HDA | Multi-módulo | Auto-geração | Open Source |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| CIROS 7 (Festo) | Não | OPC (legado) | Não | Sim (prop.) | Não | Não |
| FA³ST (Fraunhofer) | Sim | Sim | Não | Limitado | Parcial | Sim |
| Eclipse BaSyx 2.0 | Sim | Parcial | Não | Sim | Não | Sim |
| AASX Package Explorer | Sim | Não | Não | Sim | Não | Sim |
| **Faaster** | **Sim** | **Sim** | **Sim** | **Sim (7)** | **Sim** | **Sim** |

### 2.4 Digital Twin em Sistemas Modulares

- **Kritzinger et al. (2018):** taxonomia DT — Digital Model, Digital Shadow, Digital Twin (sincronização bidirecional)
- **Grieves (2014):** origem conceitual do DT como réplica virtual com ciclo de vida integrado
- **[REF retrofit]:** Mendonça et al. — retrofit de sistema legado MPS com DT via CIROS (trabalho base, limitações discutidas)
- **[REF AAS survey]:** revisão de implementações AAS em contextos industriais
- **[REF OPC UA + AAS]:** integração AAS-OPC UA — gap identificado na literatura

---

## 3. O Sistema CPS-406

### 3.1 Visão Geral

A planta **Festo CP-L-406-1** (CP-LAB-406) é um sistema de manufatura modular didático composto por 7 estações dispostas em linha, cada uma responsável por uma etapa específica do processo de produção de peças plásticas.

```
[MAGFRONT] → [MEAS] → [iDRILL] → [MAGBACK] → [MPRESS] → [OUT] → [COBOT]
   St.1        St.2      St.3       St.4        St.5      St.6     St.7
```

**Identificadores do sistema:**
- AAS ID: `urn:festo:cp-factory:aas:CP-LAB-406`
- Asset ID: `urn:festo:cp-factory:asset:CP-LAB-406`

### 3.2 Descrição das Estações

#### Estação 1 — MAGFRONT (Magazine Frontal)
- **Módulo:** CP-AM-MAG
- **Função:** Alimentação de peças — injeta workpieces na linha de produção via magazine de entrada
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-MAGFRONT`
- **PLC:** Siemens ET200SP CPU 1512SP F-1PN
- **HMI:** Siemens SIMATIC MTP700
- **RFID:** Siemens RF210R via IO-Link V1.1 (porta 1, 32 bytes)
- **Motor esteira:** OTT#SWM4033438-3, 24VDC bidirecional
- **Encoder:** Festo FES.102796 (8 pulsos/canal, 94.2 mm/rotação)
- **Operation Number:** 100

#### Estação 2 — MEAS (Medição)
- **Módulo:** CP-AM-MEASURE-V2
- **Função:** Medição dimensional das peças (altura, diâmetro)
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-MEAS`
- **PLC/HMI/RFID:** idêntico ao padrão (ET200SP + MTP700 + RF210R)
- **Operation Number:** 105

#### Estação 3 — iDRILL (Furadeira Inteligente)
- **Módulo:** CP-AM-iDRILL
- **Função:** Furação CNC das peças (furo de precisão controlado digitalmente)
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-iDRILL`
- **PLC/HMI/RFID:** padrão
- **Operation Number:** 108

#### Estação 4 — MAGBACK (Magazine Traseiro)
- **Módulo:** CP-AM-MAG (mesmo módulo que MAGFRONT)
- **Função:** Reintrodução de tampas/coberturas na linha
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-MAGBACK`
- **Operation Number:** 109

#### Estação 5 — MPRESS (Prensa Modular)
- **Módulo:** CP-AM-MPRESS (artigo 8038567)
- **Função:** Prensagem e montagem das tampas nas peças
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-MPRESS`
- **Operation Number:** 111

#### Estação 6 — OUT (Saída)
- **Módulo:** CP-AM-OUT
- **Função:** Triagem e saída das peças finalizadas por qualidade (OK/NOK/pendente)
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-OUT`
- **Operation Number:** 120

#### Estação 7 — COBOT (Robô Colaborativo)
- **Módulo:** Universal Robots UR5e
- **Função:** Manipulação colaborativa — pick & place, inspeção, paletização
- **AAS ID:** `urn:festo:cp-factory:aas:STATION-COBOT`
- **Fabricante:** Universal Robots A/S (Dinamarca)
- **Interfaces:** ControllerIO (8DI/8DO/2AI/2AO), ToolIO (2DI/2DO/2AI), OPC UA nativo
- **Operation Number:** 130

### 3.3 Hardware Padrão por Estação (1–6)

| Componente | Especificação |
|---|---|
| PLC | Siemens ET200SP CPU 1512SP F-1PN |
| HMI | Siemens SIMATIC MTP700 (art. 8189692) |
| RFID Reader | Siemens RF210R, IO-Link V1.1 |
| Motor Esteira | OTT#SWM4033438-3, 24VDC bidirecional |
| Encoder | Festo FES.102796, 8 pulsos/canal, 94.2 mm/rot |
| Stopper | VUVG-L10-M52-MT-M5-1P3 (FES.574351), 5/2 monostável 24VDC |

### 3.4 Catálogo de Peças Processadas

| Código | Descrição (EN) | Descrição (PT) |
|---|---|---|
| 101 | CP raw material black | CP matéria-prima preta |
| 102 | CP raw material grey | CP matéria-prima cinza |
| 103 | CP raw material blue | CP matéria-prima azul |
| 104 | CP raw material red | CP matéria-prima vermelha |
| 107 | CP front cover red | CP tampa frontal vermelha |
| 108 | CP front cover blue | CP tampa frontal azul |
| 109 | CP front cover grey | CP tampa frontal cinza |
| 110 | CP front cover black | CP tampa frontal preta |
| 111 | CP back cover black | CP tampa traseira preta |
| 210 | CP front cover black with CNC hole | CP tampa frontal preta com furo CNC |
| 1200 | CP black complete without board | CP preto completo sem placa |

---

## 4. Modelagem AAS V3 por Módulo

### 4.1 Hierarquia de Modelos

```
CP-LAB-406 (AAS Sistema)
├── Submodelos do sistema: Nameplate, TechnicalData, Hierarchy,
│                          Documentation, ProductionProcess, Maintenance
│
├── Station_01_MAGFRONT  (AAS Estação)
│   ├── Conveyor_Nameplate      (urn:...CP-L-LINEAR-V2-MAGFRONT:Nameplate)
│   ├── Conveyor_TechnicalData  (urn:...CP-L-LINEAR-V2-MAGFRONT:TechnicalData)
│   ├── Conveyor_Documentation  (urn:...CP-L-LINEAR-V2-MAGFRONT:Documentation)
│   ├── Module_Nameplate        (urn:...CP-AM-MAG:Nameplate)
│   ├── Module_TechnicalData    (urn:...CP-AM-MAG:TechnicalData)
│   ├── Module_Documentation    (urn:...CP-AM-MAG:Documentation)
│   ├── IOInterface             (urn:...STATION-MAGFRONT:IOInterface)
│   └── ProductionOrder         (urn:...STATION-MAGFRONT:ProductionOrder)
│
├── Station_02_MEAS  ... (mesma estrutura)
├── Station_03_iDRILL ...
├── Station_04_MAGBACK ...
├── Station_05_MPRESS ...
├── Station_06_OUT ...
│
└── Station_07_COBOT  (AAS Estação — estrutura diferenciada)
    ├── Robot_Nameplate         (urn:...UR5e-COBOT:Nameplate)
    ├── Robot_TechnicalData     (urn:...UR5e-COBOT:TechnicalData)
    ├── Robot_Documentation     (urn:...UR5e-COBOT:Documentation)
    ├── IOInterface             (urn:...STATION-COBOT:IOInterface)
    └── ProductionOrder         (urn:...STATION-COBOT:ProductionOrder)
```

**Total:** 8 arquivos AAS JSON × 8 submodelos = **56 submodelos** + submodelos do sistema

### 4.2 Estrutura do Submodelo IOInterface

O IOInterface de cada estação segue o template IDTA com semantic ID `https://admin-shell.io/idta/IOInterface/1/0`:

```
IOInterface/
├── Conveyor/
│   ├── Sensors/
│   │   ├── BG1_CarrierPresence     (bool)  — presença de carrier na esteira
│   │   ├── BG21_StopperPos         (bool)  — posição do stopper 1
│   │   ├── BG22_StopperPos         (bool)  — posição do stopper 2
│   │   ├── BG23_StopperPos         (bool)  — posição do stopper 3
│   │   ├── BG24_StopperPos         (bool)  — posição do stopper 4
│   │   ├── TF80_RFID_TagPresent    (bool)  — tag RFID presente
│   │   ├── TF80_RFID_CarrierID     (string)— ID do carrier
│   │   └── TF80_RFID_StateCode     (int)   — código de estado do carrier
│   └── Actuators/
│       ├── MB20_BeltMotor          (bool)  — motor da esteira
│       └── Y1_StopperCylinder      (bool)  — cilindro stopper
└── Module/
    ├── Sensors/  (específicos por estação)
    └── Actuators/ (específicos por estação)
```

### 4.3 Estrutura do Submodelo ProductionOrder

```
ProductionOrder/
├── CurrentOrder/
│   ├── OrderNumber     (string)
│   ├── OrderPosition   (string)
│   ├── OperationNumber (int)    — 100/105/108/109/111/120/130 por estação
│   ├── OperationName   (string)
│   ├── Resource        (string)
│   ├── CarrierID       (string)
│   ├── StateCode       (int)
│   ├── Parameter1–4    (string) — parâmetros específicos da operação
├── CurrentWorkpiece/
│   ├── PartNumber      (string)
│   ├── PartDescription (string)
│   └── QualityResult   (string) — "pending" | "OK" | "NOK"
└── WorkpieceCatalog/
    └── Part_101 … Part_1200   (11 peças catalogadas)
```

### 4.4 Problema Técnico: PathType e URLs HTTPS

O validador `path_type.py` do Faaster usa uma regex (`FILE_URI_REGEX`) que não reconhece URLs HTTPS, rejeitando todos os thumbnails e links de documentação do CPS-406.

**Solução implementada:**

```python
# Arquivo: faaster/aas_metamodel/models/path_type.py
# Adicionada primeira alternativa na regex:

FILE_URI_REGEX = re.compile(
    r"^(?:"
    r"https?://[^\s]+|"       # ← patch: URLs HTTP/HTTPS
    r"/.*|"                    # caminhos absolutos Unix
    r"\.{1,2}/.*|"             # caminhos relativos
    r"[^/:]+|"                 # nomes de arquivo simples
    r"[A-Za-z]:/.*|"           # caminhos Windows
    r"file:(?:[A-Za-z]:/.|//[^/]+/.|/.*)|"  # file:// URI
    r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)"  # base64
    r")\Z"
)
```

**Impacto:** sem o patch, todos os 56 thumbnails e todos os links de manuais falham na validação.

---

## 5. Faaster: Runtime OPC UA para AAS

### 5.1 Arquitetura do Faaster

```
┌─────────────────────────────────────────────────────────────────┐
│                          FAASTER                                │
│                                                                 │
│  AAS V3 JSON  ──►  Parser  ──►  OPC UA Address Space Builder   │
│                                          │                      │
│                                          ▼                      │
│                              OPC UA Server (Type 2)             │
│                              asyncua / python-opcua             │
│                                          │                      │
│                              ┌───────────┴──────────┐          │
│                              │                      │          │
│                         Subscriptions          TimescaleDB      │
│                         (push events)          (HDA / HDB)     │
└─────────────────────────────────────────────────────────────────┘
        ▲                           │
        │ dados físicos             │ nodes OPC UA
        │ (Modbus / MQTT / BLE)     ▼
  Estações CPS-406          Clientes OPC UA
  (PLCs Siemens +           (UaExpert, Node-RED,
   UR5e Cobot)               Python, Grafana)
```

### 5.2 Pipeline de Transformação AAS → OPC UA

| Tipo AAS | Tipo OPC UA gerado |
|---|---|
| `AssetAdministrationShell` | `Object` (raiz do namespace) |
| `Submodel` | `Object` (filho da AAS) |
| `SubmodelElementCollection` | `Object` (filho do submodel) |
| `SubmodelElementList` | `Object` com filhos indexados |
| `Property` | `Variable` (com tipo mapeado) |
| `MultiLanguageProperty` | `Variable` (array de strings localizadas) |
| `File` / `Blob` | `Variable` (string com URI/base64) |
| `ReferenceElement` | `Variable` (NodeId referenciado) |
| `Operation` | `Method` com Input/Output args |
| `AnnotatedRelationshipElement` | `HasComponent` reference |

**Mapeamento de tipos de valor:**

| AAS valueType | OPC UA DataType |
|---|---|
| `xs:boolean` | `Boolean` |
| `xs:int` / `xs:integer` | `Int32` |
| `xs:double` / `xs:float` | `Double` |
| `xs:string` | `String` |
| `xs:dateTime` | `DateTime` |

### 5.3 Historical Data Access (HDA)

O Faaster persiste cada publicação OPC UA no TimescaleDB com schema:

```sql
CREATE TABLE aas_timeseries (
    time        TIMESTAMPTZ NOT NULL,
    station_id  TEXT NOT NULL,           -- ex: "STATION-MAGFRONT"
    submodel_id TEXT NOT NULL,           -- ex: "STATION-MAGFRONT:IOInterface"
    id_short    TEXT NOT NULL,           -- ex: "BG1_CarrierPresence"
    value       JSONB,                   -- valor tipado
    quality     TEXT DEFAULT 'Good'      -- OPC UA quality flag
);
SELECT create_hypertable('aas_timeseries', 'time');
```

Consulta de histórico por `idShort`:
```sql
SELECT time, value
FROM aas_timeseries
WHERE station_id = 'STATION-iDRILL'
  AND id_short   = 'BG1_CarrierPresence'
  AND time BETWEEN NOW() - INTERVAL '1 hour' AND NOW()
ORDER BY time;
```

### 5.4 Deploy por Módulo

Cada estação é um container independente:

```yaml
# docker-compose.yml (exemplo para 3 estações)
services:
  faaster-magfront:
    image: open-aas/faaster:latest
    environment:
      AAS_FILE: /models/station_magfront.json
      OPC_UA_PORT: 4840
      TIMESCALE_DSN: postgresql://faaster:pw@timescaledb/aas
    volumes:
      - ./cp_406:/models

  faaster-idrill:
    image: open-aas/faaster:latest
    environment:
      AAS_FILE: /models/station_idrill.json
      OPC_UA_PORT: 4841
      TIMESCALE_DSN: postgresql://faaster:pw@timescaledb/aas

  timescaledb:
    image: timescale/timescaledb:latest-pg14
```

---

## 6. Plano de Avaliação Experimental

### 6.1 Experimento 1 — Latência de Sincronização por Estação

**Objetivo:** medir o tempo entre evento físico (mudança de sensor no PLC) e atualização no nó OPC UA do Faaster.

**Protocolo:**
```
Para cada estação (1–7):
  Para i = 1 to 100:
    1. Acionar evento físico (ex: peça passa pelo sensor BG1)
    2. Registrar t0 = timestamp no PLC (resolução 1ms)
    3. Registrar t1 = timestamp de recebimento no cliente OPC UA
    4. LS_i = t1 - t0
  Calcular: média, σ, p50, p95, p99
```

**Resultado esperado:** tabela + boxplot por estação

| Estação | Média (ms) | σ (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|
| MAGFRONT | — | — | — | — |
| MEAS | — | — | — | — |
| iDRILL | — | — | — | — |
| MAGBACK | — | — | — | — |
| MPRESS | — | — | — | — |
| OUT | — | — | — | — |
| COBOT | — | — | — | — |

### 6.2 Experimento 2 — Fidelidade do Modelo

**Objetivo:** quantificar o desvio entre leituras do sensor físico e o valor exposto pelo DT.

**Protocolo:**
```
Para cada sensor analógico de cada estação:
  Para i = 1 to 50:
    1. Ler valor diretamente do PLC (ground truth = v_phys)
    2. Ler valor do nó OPC UA correspondente (v_dt)
    3. erro_i = v_phys - v_dt
  Calcular:
    MAE  = Σ|erro_i| / N
    RMSE = √(Σerro_i² / N)
    FM   = (1 - MAE / range_sensor) × 100%
```

**Resultado esperado:** tabela MAE/RMSE/FM por tipo de sensor por estação

### 6.3 Experimento 3 — Escalabilidade do Faaster

**Objetivo:** avaliar comportamento do sistema com 1 a 7 AAS ativos simultaneamente.

**Protocolo:**
```
Para N = 1, 2, 3, 4, 5, 6, 7 estações ativas:
  1. Iniciar N instâncias Faaster via docker-compose
  2. Aguardar 60s de estabilização
  3. Durante 300s de steady-state, medir a cada 10s:
     - CPU total (%)
     - RAM RSS total (MB)
     - Latência OPC UA média
     - Throughput total (publicações/s)
  4. Registrar médias e desvios
```

**Resultado esperado:** curvas de escalabilidade (CPU, RAM, latência, throughput) vs. N

### 6.4 Experimento 4 — OEE com vs. sem DT

**Objetivo:** demonstrar impacto operacional do DT na eficiência da linha.

**Protocolo:**
```
Período A (10 dias): produção SEM DT ativo
  - Monitoramento manual por operador
  - Registro de falhas em planilha

Período B (10 dias): produção COM Faaster ativo
  - Detecção automática de falhas via threshold em nós OPC UA
  - Alertas em tempo real via Node-RED

Métricas coletadas em ambos os períodos:
  - MTTD (Mean Time To Detect) uma falha
  - MTTR (Mean Time To Repair)
  - Downtime total acumulado
  - Throughput (peças/hora)
  - OEE = Disponibilidade × Desempenho × Qualidade
```

**Resultado esperado:** tabela comparativa A vs. B com % de melhoria

### 6.5 Experimento 5 — Interoperabilidade

**Objetivo:** validar que o servidor OPC UA gerado pelo Faaster é consumível por clientes heterogêneos.

**Clientes testados:**

| Cliente | Tipo | Fabricante |
|---|---|---|
| UaExpert | GUI de inspeção | Unified Automation |
| Node-RED | Dashboard industrial | OpenJS Foundation |
| Python `asyncua` | Cliente programático | open-source |
| OPC Foundation CTT | Compliance Test Tool | OPC Foundation |

**Resultado esperado:** tabela binária (compatível / não compatível) por cliente × funcionalidade OPC UA (Browse, Read, Write, Subscribe, HDA)

### 6.6 Experimento 6 — Avaliação de Maturidade RAMI 4.0

**Critérios e indicadores quantitativos:**

| Critério | Indicador Quantitativo | Legado | Com DT |
|---|---|---|---|
| F1 — Automação | % ações manuais eliminadas | — % | — % |
| F2 — Integração | N° sistemas integrados OPC UA / total | — / 7 | — / 7 |
| F3 — Dispositivos Inteligentes | N° sensores com semantic ID / total | — / — | — / — |
| F4 — Análise de Dados | GB dados históricos acessíveis (HDA/mês) | 0 GB | — GB |
| F5 — Flexibilidade | N° configs produção testadas no DT sem parar linha | 0 | — |

---

## 7. Análise de Maturidade RAMI 4.0 — Sistema CPS-406

### 7.1 Sistema Legado (antes do DT)

| Critério | Nível | Justificativa |
|---|:---:|---|
| F1 — Automação | 3 | PLCs Siemens com lógica ladder, sem supervisão integrada |
| F2 — Integração | 2 | Estações isoladas, sem troca de dados padronizada entre módulos |
| F3 — Dispositivos Inteligentes | 2 | RFID presente mas sem semântica; sensores sem IDs padronizados |
| F4 — Análise de Dados | 1 | Sem coleta histórica; sem dashboard; análise apenas manual |
| F5 — Flexibilidade | 2 | Reconfiguração apenas física (trocar módulos manualmente) |

### 7.2 Sistema Atualizado (com AAS V3 + Faaster)

| Critério | Nível | Justificativa |
|---|:---:|---|
| F1 — Automação | 4 | DT com monitoramento em tempo real + alertas automáticos |
| F2 — Integração | 5 | 7 AAS interoperáveis via OPC UA + semantic IDs padronizados |
| F3 — Dispositivos Inteligentes | 4 | RFID + sensores com semantic IDs ECLASS/IDTA |
| F4 — Análise de Dados | 4 | HDA via TimescaleDB, Grafana dashboard, queries históricas |
| F5 — Flexibilidade | 4 | Scripts de produção configuráveis via ProductionOrder no DT |

---

## 8. Estrutura Prevista do Artigo (para submissão IEEE)

```
I. Introduction
II. Background and Related Work
    A. Asset Administration Shell V3
    B. OPC UA Type 2 Reactive Servers
    C. Digital Twins in Modular Manufacturing
    D. Comparison with Existing Tools
III. The Festo CP-406 Production System
    A. System Overview and Stations
    B. Hardware Architecture
    C. Production Process
IV. AAS V3 Modeling Approach
    A. Hierarchy Design
    B. Submodel Structure (8 per station)
    C. Semantic IDs and PathType
    D. COBOT (UR5e) Modeling
V. Faaster: OPC UA Runtime for AAS
    A. Architecture
    B. AAS-to-OPC-UA Mapping
    C. Historical Data Access (TimescaleDB)
    D. PathType Patch for HTTPS URLs
    E. Containerized Deployment
VI. Experimental Evaluation
    A. Synchronization Latency (Exp. 1)
    B. Model Fidelity (Exp. 2)
    C. Scalability (Exp. 3)
    D. OEE Impact (Exp. 4)
    E. Interoperability (Exp. 5)
    F. RAMI 4.0 Maturity (Exp. 6)
VII. Discussion
    A. Contributions vs. State of Art
    B. Limitations
    C. Future Work
VIII. Conclusion
References
```

**Estimativa de páginas:** 10–12 páginas IEEE double-column  
**Estimativa de referências:** 45–55

---

## 9. Artefatos a Disponibilizar (Open Access)

| Artefato | Localização | Formato |
|---|---|---|
| AAS JSON — 7 estações + sistema | github.com/open-aas/CPS-406 | JSON (AAS V3) |
| Faaster runtime | github.com/open-aas/faaster | Python 3.11+ |
| Docker-compose CPS-406 | github.com/open-aas/CPS-406 | YAML |
| Dataset de sensores | Zenodo (DOI a gerar) | CSV / Parquet |
| Scripts de experimentos | github.com/open-aas/CPS-406/experiments | Python |
| Figuras vetoriais | github.com/open-aas/CPS-406/paper/figures | SVG / PDF |

---

## 10. Journals Alvo e Cronograma

### Journals Ordenados por Prioridade

| Prioridade | Journal | IF | Qualis | Prazo médio revisão |
|:---:|---|:---:|:---:|---|
| 1 | IEEE Trans. Industrial Informatics | ~12.3 | A1 | 3–6 meses |
| 2 | Robotics & Computer-Integrated Mfg | ~10.4 | A1 | 4–6 meses |
| 3 | Journal of Manufacturing Systems | ~9.1 | A1 | 3–5 meses |
| 4 | Computers & Industrial Engineering | ~7.9 | A1 | 3–4 meses |
| 5 | IEEE Access | ~3.4 | A2 | 4–8 semanas |

### Cronograma Sugerido

| Fase | Atividade | Duração |
|---|---|---|
| **F1** | Completar modelos AAS V3 (7 estações) | 2 semanas |
| **F2** | Patch PathType + validação Faaster | 1 semana |
| **F3** | Setup experimental (Docker + TimescaleDB) | 1 semana |
| **F4** | Execução dos 6 experimentos | 3 semanas |
| **F5** | Análise estatística dos resultados | 1 semana |
| **F6** | Escrita do artigo (seções I–VIII) | 4 semanas |
| **F7** | Revisão interna + ajustes | 2 semanas |
| **F8** | Submissão | — |
| **Total** | | **~14 semanas** |

---

## 11. Checklist de Pré-Submissão

### Modelos AAS
- [ ] 7 arquivos JSON de estação validados pelo metamodel Faaster
- [ ] 1 arquivo JSON de sistema (CP-LAB-406) completo
- [ ] Todos os thumbnails com URL HTTPS válida
- [ ] Todos os links de documentação verificados (manuais, datasheets)
- [ ] Patch PathType aplicado e testado

### Experimentos
- [ ] Experimento 1: latência (N=100 por estação, 7 estações)
- [ ] Experimento 2: fidelidade (sensores analógicos, N=50)
- [ ] Experimento 3: escalabilidade (1–7 AAS simultâneos)
- [ ] Experimento 4: OEE (10 dias A + 10 dias B)
- [ ] Experimento 5: interoperabilidade (4 clientes OPC UA)
- [ ] Experimento 6: maturidade RAMI (critérios F1–F5 quantificados)

### Artigo
- [ ] Abstract ≤ 250 palavras com problema/método/resultado/impacto
- [ ] Revisão literatura ≥ 40 referências (2020–2025)
- [ ] Análise estatística com intervalos de confiança 95%
- [ ] Tabela comparativa com FA³ST, BaSyx, CIROS
- [ ] Seção de limitações honesta
- [ ] Trabalhos futuros concretos (não vagos)
- [ ] Verificação de similaridade ≤ 20% (iThenticate)
- [ ] Figuras vetoriais (SVG/PDF) ≥ 300 DPI para JPEG

### Open Access
- [ ] Repositório GitHub público (open-aas/CPS-406)
- [ ] DOI Zenodo para dataset de sensores
- [ ] Docker-compose funcional e documentado
- [ ] README com instruções de reprodução passo a passo

---

## 12. Referências Fundamentais (BibTeX base)

```bibtex
@techreport{IEC63278-2,
  title        = {{Asset Administration Shell -- Part 2: Metamodel (V3.0)}},
  institution  = {IEC},
  number       = {IEC 63278-2},
  year         = {2023}
}

@techreport{IEC62541,
  title        = {{OPC Unified Architecture (OPC UA)}},
  institution  = {IEC},
  number       = {IEC 62541},
  year         = {2020}
}

@article{Grieves2014,
  author  = {Grieves, Michael},
  title   = {{Digital Twin: Manufacturing Excellence through Virtual Factory Replication}},
  year    = {2014}
}

@article{Kritzinger2018,
  author  = {Kritzinger, Werner and Karner, Matthias and Traar, Georg
             and Henjes, Jan and Sihn, Wilfried},
  title   = {{Digital Twin in manufacturing: A categorical literature review
              and classification}},
  journal = {IFAC-PapersOnLine},
  volume  = {51},
  number  = {11},
  pages   = {1016--1022},
  year    = {2018}
}

@article{Mendonca2023,
  author  = {Mendon{\c{c}}a, Rafael da Silva and de Medeiros, Renan Landau Paiva
             and de Lucena Jr., Vicente Ferreira},
  title   = {{Development of a Novel Retrofit Framework Considering Industry 4.0
              Concepts: A Case Study of a Didactic Manufacture Production System}},
  journal = {IEEE ...},
  year    = {2023}
}

% A buscar na literatura (2022-2025):
% - AAS + OPC UA integration survey
% - RAMI 4.0 maturity models
% - Platform Industrie 4.0 whitepapers
% - IDTA Submodel Templates (IOInterface, ProductionOrder)
% - Collaborative robot digital twin
% - TimescaleDB for industrial HDA
% - FA3ST Service (Fraunhofer)
% - Eclipse BaSyx AAS V3
```

---

*Proposta gerada com base no artigo modelo `tesis_final.tex`, nos modelos AAS V3 do CPS-406 e na arquitetura do Faaster.*  
*Repositório: github.com/open-aas/CPS-406 | Branch: artigo*
