# CPS-406 — Asset Administration Shell

![AAS Version](https://img.shields.io/badge/AAS-V3%20(IEC%2063278)-blue)
![Standard](https://img.shields.io/badge/Standard-IEC%2063278%20Part%202%20v3.0-informational)
![Language](https://img.shields.io/badge/Languages-EN%20%7C%20PT-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Digital twin do sistema de manufatura **Festo CP-L-406-1** implementado segundo o padrão **Asset Administration Shell V3** (IEC 63278 / Parte 2 v3.0). O projeto modela cada componente da linha de produção como um AAS independente, contendo submodelos padronizados de identificação, dados técnicos, documentação, interface de E/S e ordem de produção.

---

## Índice

1. [Visão geral do sistema](#visão-geral-do-sistema)
2. [Estrutura do repositório](#estrutura-do-repositório)
3. [AAS do sistema](#aas-do-sistema-cp_lab_406_systemjson)
4. [Estações](#estações)
5. [Estrutura de submodelos](#estrutura-de-submodelos)
6. [Catálogo de peças](#catálogo-de-peças)
7. [Esquema de identificadores URN](#esquema-de-identificadores-urn)
8. [Conformidade AAS V3](#conformidade-aas-v3)
9. [Autores](#autores)

---

## Visão geral do sistema

O **CP-L-406-1** é uma linha de produção didática modular do Festo CP Factory composta por **7 estações** interligadas por esteiras transportadoras lineares. A linha realiza a montagem completa de capas de controladores programáveis (CP), desde a alimentação da matéria-prima até a entrega da peça acabada.

| Atributo | Valor |
|----------|-------|
| Fabricante | Festo Didactic SE |
| Código de pedido | CP-L-406-1 |
| Artigo | 8092834 |
| Tensão de operação | 24 VDC |
| Pressão de operação | 6 bar |
| Número de estações | 7 |
| Padrão AAS | IEC 63278 Parte 2 v3.0 |
| Idiomas | Inglês (en) + Português (pt) |

---

## Estrutura do repositório

```
CPS-406/
├── README.md
└── cp_406/
    ├── cp_lab_406_system.json       # AAS do sistema completo
    ├── station_magfront.json        # Estação 1 — Magazine (frente)
    ├── station_meas.json            # Estação 2 — Medição
    ├── station_idrill.json          # Estação 3 — Furadeira inteligente
    ├── station_magback.json         # Estação 4 — Magazine (trás)
    ├── station_mpress.json          # Estação 5 — Prensa pneumática
    ├── station_out.json             # Estação 6 — Saída
    ├── station_cobot.json           # Estação 7 — Robô colaborativo UR5e
    ├── thumbnails/
    │   ├── system_406_1.png
    │   ├── mag_front.png
    │   ├── measure.png
    │   ├── drill.png
    │   ├── mag_back.png
    │   ├── press.png
    │   ├── output.png
    │   └── cobot.png
    └── docs/
        ├── manual_en_cp_406.pdf     # Manual completo do sistema
        ├── workpieces.txt           # Catálogo de peças produzidas
        └── documens_links.txt       # Links para manuais por estação
```

---

## AAS do sistema (`cp_lab_406_system.json`)

Representa o sistema como um todo e agrega referências hierárquicas a todas as estações.

```
AAS ID:   urn:festo:cp-factory:aas:CP-LAB-406
Asset ID: urn:festo:cp-factory:asset:CP-LAB-406
```

| Submodelo | ID | Descrição |
|-----------|----|-----------|
| `Nameplate` | `…:CP-LAB-406:Nameplate` | Placa de identificação — fabricante, artigo, código de pedido |
| `TechnicalData` | `…:CP-LAB-406:TechnicalData` | Dados técnicos — tensão, pressão, dimensões, número de estações |
| `Hierarchy` | `…:CP-LAB-406:Hierarchy` | Referências hierárquicas às 7 estações via `ReferenceElement` |
| `Documentation` | `…:CP-LAB-406:Documentation` | Manual do sistema em PDF |
| `ProductionProcess` | `…:CP-LAB-406:ProductionProcess` | Sequência de operações por estação |
| `Maintenance` | `…:CP-LAB-406:Maintenance` | Plano de manutenção preventiva e corretiva |

---

## Estações

### Visão geral

| # | ID | Arquivo | Módulo de aplicação | Função |
|---|----|---------|---------------------|--------|
| 1 | `STATION-MAGFRONT` | `station_magfront.json` | CP-AM-MAG | Alimentação de matéria-prima |
| 2 | `STATION-MEAS` | `station_meas.json` | CP-AM-MEASURE-V2 | Medição e classificação da peça |
| 3 | `STATION-iDRILL` | `station_idrill.json` | CP-AM-iDRILL | Furação CNC da tampa frontal |
| 4 | `STATION-MAGBACK` | `station_magback.json` | CP-AM-MAG | Alimentação da tampa traseira |
| 5 | `STATION-MPRESS` | `station_mpress.json` | CP-AM-MPRESS | Prensagem das tampas |
| 6 | `STATION-OUT` | `station_out.json` | CP-AM-OUT | Saída e entrega da peça acabada |
| 7 | `STATION-COBOT` | `station_cobot.json` | Universal Robots UR5e | Pick and place / montagem colaborativa |

Todas as estações 1–6 utilizam a esteira **Festo CP-L-LINEAR-V2** (artigo D12501, código CP-L-LINEAR-V2-C11M0) como módulo base com PLC **Siemens ET200SP CPU 1512SP F-1PN**, HMI **Siemens SIMATIC MTP700** e leitor RFID **Siemens RF210R** (IO-Link V1.1).

---

### Estação 1 — MAGFRONT

**Função:** Alimentação de peças brutas na linha. O magazine empilha as matérias-primas e insere uma a uma nos portadores de pallete via cilindro pneumático ejetor.

**Documentação oficial:**
- [Manual CP-AM-MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/manual_en.pdf)
- [Esquemáticos CP-AM-MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/schematics.pdf)

---

### Estação 2 — MEAS

**Função:** Medição da altura da peça bruta por sensor de deslocamento analógico (IO-Link) para detectar cor/tipo e verificar conformidade dimensional. O resultado determina o roteamento da peça nas estações seguintes.

**Documentação oficial:**
- [Manual CP-AM-MEASURE-V2](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/manual_en.pdf)
- [Esquemáticos CP-AM-MEASURE-V2](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/schematics.pdf)
- [Label da tampa frontal](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/front_cover_label.pdf)

---

### Estação 3 — iDRILL

**Função:** Furação CNC da tampa frontal quando requerida pela ordem de produção (peça No. 210). O spindle é controlado por servo com monitoramento de força e posição.

**Documentação oficial:**
- [Manual CP-AM-iDRILL](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-iDRILL/files/manual_en.pdf)
- [Esquemáticos CP-AM-iDRILL](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-iDRILL/files/schematics.pdf)

---

### Estação 4 — MAGBACK

**Função:** Alimentação da tampa traseira (back cover) sobre a peça já posicionada no portador de pallete, preparando-a para a etapa de prensagem.

**Documentação oficial:**
- [Manual CP-AM-MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/manual_en.pdf)
- [Esquemáticos CP-AM-MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/schematics.pdf)

---

### Estação 5 — MPRESS

**Função:** Prensagem da tampa traseira sobre a frontal utilizando músculo pneumático (fluidic muscle) com regulação de força. A força de prensagem é monitorada continuamente por sensor analógico.

**Artigo:** 8038567 | **Código:** CP-AM-MPRESS

| Atuador | Tipo |
|---------|------|
| Músculo pneumático | Fluidic muscle — contração para prensagem |
| Cilindro de fixação | Pneumático — trava o pallete durante a prensagem |

**Sensores:** posição do cilindro (cima/baixo), presença de tampa traseira, força de prensagem analógica.

**Documentação oficial:**
- [Manual CP-AM-PRESS](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-PRESS/files/manual_en.pdf)
- [Esquemáticos CP-AM-PRESS](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-PRESS/files/schematics.pdf)

---

### Estação 6 — OUT

**Função:** Retirada da peça acabada do portador de pallete e entrega ao operador ou sistema downstream, com possibilidade de triagem OK/NOK.

**Documentação oficial:**
- [Manual CP-AM-OUT](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-OUT/files/manual_en.pdf)
- [Esquemáticos CP-AM-OUT](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-OUT/files/schematics.pdf)

---

### Estação 7 — COBOT (Universal Robots UR5e)

**Função:** Operações de pick and place e montagem colaborativa. O robô interage com portadores de pallete da linha, podendo realizar alimentação, montagem ou inspeção de peças em colaboração segura com operadores humanos.

#### Especificações técnicas

| Especificação | Valor |
|---------------|-------|
| Graus de liberdade | 6 |
| Payload máximo | 5 kg |
| Alcance máximo | 850 mm |
| Repetibilidade | ± 0,03 mm |
| Velocidade TCP máx. | 1,0 m/s |
| Peso do braço | 20,6 kg |
| Controlador | CB5 (e-Series) |
| Alimentação | 100–240 VAC, 50/60 Hz |
| Consumo típico | 200 W |
| Temperatura de operação | 0–50 °C |
| Certificação de segurança | PLd Cat.3 (ISO 13849) |
| Sensor de força/torque | 6 eixos integrado no pulso |

#### Interfaces de comunicação

| Protocolo | Detalhe |
|-----------|---------|
| Modbus TCP | Porta 502 — cliente/servidor |
| PROFINET IO | Dispositivo IO via URCap |
| EtherNet/IP | Adaptador |
| OPC UA | Servidor — porta 4840 |
| RTDE | Real-Time Data Exchange — porta 30004 |

#### Entradas e saídas

| Interface | Entradas | Saídas |
|-----------|----------|--------|
| Controlador CB5 — digital | 8 (DI0–DI7) | 8 (DO0–DO7) |
| Controlador CB5 — analógico | 2 (0–10V / 4–20mA) | 2 (0–10V / 4–20mA) |
| Segurança | 8 | 4 |
| Flange da ferramenta — digital | 2 | 2 |
| Flange da ferramenta — analógico | 2 | — |

#### Documentação oficial

- [Manual do usuário UR5e (EN) — SW5.19](https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf)
- [Manual do usuário UR5e (PT) — PolyScopeX SW10.12](https://www.universal-robots.com/manuals/pt/PDF/SW10_12/user-manual-UR5e-PolyX-PDF_online/718-749-00_UR5e%20PolyScope%20X_User_Manual_PolyScopeX_pt_Global.pdf)
- [Datasheet UR5e e-Series](https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf)
- [Fact Sheet UR5e (PT)](https://www.universal-robots.com/media/1820977/07_2021_ur5e_fact_sheet_pt_web.pdf)

---

## Estrutura de submodelos

### Estações 1–6 (8 submodelos por estação)

```
station_{name}.json
│
├── Conveyor_Nameplate          # Identificação da esteira CP-L-LINEAR-V2
├── Conveyor_TechnicalData      # PLC, HMI, RFID, motor, encoder, pneumática, I/O
├── Conveyor_Documentation      # Manual e esquemáticos da esteira
│
├── Module_Nameplate            # Identificação do módulo de aplicação
├── Module_TechnicalData        # Função, atuadores, sensores, dimensões, I/O do módulo
├── Module_Documentation        # Manual e esquemáticos do módulo
│
├── IOInterface                 # Todos os sinais de sensores e atuadores
│   ├── Conveyor/
│   │   ├── Sensors             # BG1_CarrierPresence, BG21–BG24_StopperPos,
│   │   │                       # TF80_RFID_TagPresent, TF80_RFID_CarrierID,
│   │   │                       # TF80_RFID_StateCode
│   │   └── Actuators           # MB20_BeltMotor, Y1_StopperCylinder
│   └── Module/
│       ├── Sensors             # Específicos do módulo de aplicação
│       └── Actuators           # Específicos do módulo de aplicação
│
└── ProductionOrder             # Ordem MES ativa e peça no portador
    ├── CurrentOrder            # OrderNumber, OrderPosition, OperationNumber,
    │                           # OperationName, Resource, CarrierID, StateCode,
    │                           # Parameter1–Parameter4
    ├── CurrentWorkpiece        # PartNumber, PartDescription, QualityResult
    └── WorkpieceCatalog        # Catálogo de todas as peças possíveis
```

### Estação 7 — COBOT (5 submodelos)

```
station_cobot.json
│
├── Robot_Nameplate             # Identificação do UR5e (Universal Robots A/S)
├── Robot_TechnicalData         # Cinemática, elétrica, comunicação, segurança
├── Robot_Documentation         # Manuais oficiais Universal Robots (EN + PT)
│
├── IOInterface
│   ├── ControllerIO/
│   │   ├── DigitalInputs       # DI0–DI7 (e-stop, safeguard, start, pallet, gripper…)
│   │   ├── DigitalOutputs      # DO0–DO7 (ready, cycle complete, gripper, fault…)
│   │   ├── AnalogInputs        # AI0–AI1
│   │   └── AnalogOutputs       # AO0–AO1
│   ├── ToolIO                  # TDI0–TDI1, TDO0–TDO1, TAI0–TAI1
│   └── RobotState              # RobotMode, SafetyMode, TCPForce_N, ProgramRunning
│
└── ProductionOrder
    ├── CurrentOrder            # OrderNumber, OperationNumber, CarrierID, StateCode…
    ├── CurrentWorkpiece        # PartNumber, PartDescription, QualityResult
    └── WorkpieceCatalog        # Peças manipuláveis pelo robô
```

### Semântica dos submodelos

| Submodelo | Semantic ID |
|-----------|-------------|
| Nameplate | `https://admin-shell.io/zvei/nameplate/2/0/Nameplate` |
| TechnicalData | `https://admin-shell.io/ZVEI/TechnicalData/Submodel/1/2` |
| Documentation | `https://admin-shell.io/DigiWin/ManufacturerDocumentation/0/1/Documentation` |
| IOInterface | `https://admin-shell.io/idta/IOInterface/1/0` |
| ProductionOrder | `https://admin-shell.io/idta/ProductionOrder/1/0` |
| Hierarchy | `https://admin-shell.io/idta/HierarchicalStructures/1/0` |

---

## Catálogo de peças

| Nº | Descrição (EN) | Descrição (PT) |
|----|----------------|----------------|
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

## Esquema de identificadores URN

```
# Sistema
urn:festo:cp-factory:aas:CP-LAB-406
urn:festo:cp-factory:asset:CP-LAB-406
urn:festo:cp-factory:sm:CP-LAB-406:{SubmodelName}

# Estações
urn:festo:cp-factory:aas:STATION-{NAME}
urn:festo:cp-factory:asset:STATION-{NAME}

# Submodelos da esteira
urn:festo:cp-factory:sm:CP-L-LINEAR-V2-{STATION}:{SubmodelName}

# Submodelos do módulo de aplicação
urn:festo:cp-factory:sm:CP-AM-{STATION}:{SubmodelName}

# Submodelos IOInterface e ProductionOrder
urn:festo:cp-factory:sm:STATION-{STATION}:{SubmodelName}

# Submodelos do COBOT
urn:festo:cp-factory:sm:UR5e-COBOT:{SubmodelName}
```

| Estação | `{NAME}` / `{STATION}` |
|---------|------------------------|
| Magazine frente | `MAGFRONT` |
| Medição | `MEAS` |
| Furadeira | `iDRILL` |
| Magazine trás | `MAGBACK` |
| Prensa | `MPRESS` |
| Saída | `OUT` |
| Robô colaborativo | `COBOT` |

---

## Conformidade AAS V3

Todos os arquivos atendem integralmente à especificação **IEC 63278 Parte 2 v3.0**:

| Requisito | Status |
|-----------|--------|
| `modelType` em todos os elementos | Implementado |
| `SubmodelElementCollection.value` (não `submodelElements`) | Implementado |
| `File.contentType` (não `mimeType`) | Implementado |
| `globalAssetId` como string simples | Implementado |
| `ExternalReference` e `ModelReference` com tipagem explícita | Implementado |
| Descrições bilíngues `en` + `pt` em todos os submodelos e propriedades | Implementado |
| `conceptDescriptions: []` em todos os arquivos | Implementado |
| `defaultThumbnail` com `path` e `contentType` em todos os AAS | Implementado |

---

## Manutenção

Manual de manutenção comum a todas as estações Festo CP Factory:

- [CP Factory Maintenance Manual — 2023.07 (EN)](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/common/files/CP-Maintenance_Manual-2023.07-en.pdf)

---

## Autores

| Autor | GitHub |
|-------|--------|
| Evaldo Cardoso | [@Evaldoes](https://github.com/Evaldoes) |
| Alison Almeida | [@alisonsalmeida](https://github.com/alisonsalmeida) |
