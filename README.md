# CPS-406 — Asset Administration Shell

Digital twin do sistema de manufatura **Festo CP-L-406-1** modelado em **AAS V3** (IEC 63278 / Parte 2 v3.0), compatível com Eclipse BaSyx v2.

---

## Estrutura do repositório

```
cp_406/
├── cp_lab_406_system.json     # AAS do sistema completo CP-LAB-406
├── station_magfront.json      # Estação 1 — Magazine (frente)
├── station_meas.json          # Estação 2 — Medição
├── station_idrill.json        # Estação 3 — Furadeira inteligente (iDRILL)
├── station_magback.json       # Estação 4 — Magazine (trás)
├── station_mpress.json        # Estação 5 — Prensa pneumática (MPRESS)
├── station_out.json           # Estação 6 — Saída (OUT)
├── station_cobot.json         # Estação 7 — Robô colaborativo UR5e (COBOT)
├── thumbnails/                # Imagens das estações e do sistema
└── docs/                      # Documentos auxiliares (manuais, catálogo de peças)
```

---

## Estações

| # | ID | Arquivo | Equipamento |
|---|----|---------|-------------|
| 1 | `STATION-MAGFRONT` | `station_magfront.json` | Esteira Linear V2 + Magazine (frente) |
| 2 | `STATION-MEAS` | `station_meas.json` | Esteira Linear V2 + Módulo de Medição V2 |
| 3 | `STATION-IDRILL` | `station_idrill.json` | Esteira Linear V2 + Furadeira iDRILL |
| 4 | `STATION-MAGBACK` | `station_magback.json` | Esteira Linear V2 + Magazine (trás) |
| 5 | `STATION-MPRESS` | `station_mpress.json` | Esteira Linear V2 + Prensa a Músculo (MPRESS) |
| 6 | `STATION-OUT` | `station_out.json` | Esteira Linear V2 + Módulo de Saída |
| 7 | `STATION-COBOT` | `station_cobot.json` | Robô Colaborativo Universal Robots UR5e |

---

## Submodelos por estação

Cada arquivo de estação contém os seguintes submodelos:

| Submodelo | Descrição |
|-----------|-----------|
| `Conveyor_Nameplate` | Placa de identificação da esteira (Festo CP-L-LINEAR-V2) |
| `Conveyor_TechnicalData` | Dados técnicos da esteira (PLC, HMI, RFID, motores, pneumática) |
| `Conveyor_Documentation` | Manuais e esquemáticos da esteira |
| `Module_Nameplate` | Placa de identificação do módulo de aplicação |
| `Module_TechnicalData` | Dados técnicos do módulo de aplicação |
| `Module_Documentation` | Manuais e esquemáticos do módulo |
| `IOInterface` | Mapeamento de entradas/saídas de sensores e atuadores |
| `ProductionOrder` | Ordem de produção MES ativa e peça no portador de pallete |

> A estação **COBOT** segue estrutura adaptada: `Robot_Nameplate`, `Robot_TechnicalData`, `Robot_Documentation`, `IOInterface` e `ProductionOrder`.

---

## Submodelos do sistema (`cp_lab_406_system.json`)

| Submodelo | Descrição |
|-----------|-----------|
| `Nameplate` | Identificação do sistema CP-L-406-1 |
| `TechnicalData` | Dados técnicos gerais do sistema |
| `Hierarchy` | Referências hierárquicas às 7 estações |
| `Documentation` | Manual do sistema |
| `ProductionProcess` | Sequência de operações de produção |
| `Maintenance` | Informações de manutenção |

---

## Identificadores AAS (URNs)

```
Sistema:    urn:festo:cp-factory:aas:CP-LAB-406
Estações:   urn:festo:cp-factory:aas:STATION-{NAME}
Submodelos: urn:festo:cp-factory:sm:{COMPONENT}:{SubmodelName}
Assets:     urn:festo:cp-factory:asset:{ID}
```

---

## Peças produzidas (WorkpieceCatalog)

| Nº | Descrição |
|----|-----------|
| 101–104 | Matéria-prima (preta, cinza, azul, vermelha) |
| 107–109 | Tampa frontal (vermelha, azul, cinza) |
| 110 | Tampa frontal preta (No. 110) |
| 111 | Tampa traseira preta (No. 111) |
| 210 | Tampa frontal preta com furo CNC (No. 210) |
| 1200 | CP preto completo sem placa (No. 1200) |

---

## Stack de execução

Compatível com **Eclipse BaSyx v2**:

| Serviço | Porta padrão |
|---------|-------------|
| aas-env | 8081 |
| aas-registry | 8082 |
| sm-registry | 8083 |
| aas-web-ui | 3000 |

---

## Conformidade AAS V3

- `modelType` em todos os elementos
- `SubmodelElementCollection.value` (não `submodelElements`)
- `File.contentType` (não `mimeType`)
- `globalAssetId` como string
- Descrições bilíngues (`en` + `pt`) em todos os submodelos e propriedades
- `conceptDescriptions: []` presente em todos os arquivos
