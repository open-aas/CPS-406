# CPS-406 — Asset Administration Shell

Digital twin do sistema de manufatura **Festo CP-L-406-1** modelado em **AAS V3** (IEC 63278 / Parte 2 v3.0).

O sistema CP-L-406-1 é uma linha de produção didática modular do laboratório Festo CP Factory composta por 7 estações interligadas por esteiras transportadoras, responsável por montar capas de controladores programáveis (CP). Cada estação é representada como um AAS independente contendo submodelos de identificação, dados técnicos, documentação, interface de E/S e ordem de produção.

---

## Estrutura do repositório

```
cp_406/
├── cp_lab_406_system.json     # AAS do sistema completo (CP-LAB-406)
├── station_magfront.json      # Estação 1 — Magazine frente (MAGFRONT)
├── station_meas.json          # Estação 2 — Medição (MEAS)
├── station_idrill.json        # Estação 3 — Furadeira inteligente (iDRILL)
├── station_magback.json       # Estação 4 — Magazine trás (MAGBACK)
├── station_mpress.json        # Estação 5 — Prensa pneumática (MPRESS)
├── station_out.json           # Estação 6 — Saída (OUT)
├── station_cobot.json         # Estação 7 — Robô colaborativo UR5e (COBOT)
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
    ├── manual_en_cp_406.pdf   # Manual completo do sistema CP-406
    ├── workpieces.txt         # Catálogo de peças produzidas
    └── documens_links.txt     # Links para manuais e esquemáticos por estação
```

---

## Sistema — `cp_lab_406_system.json`

**AAS ID:** `urn:festo:cp-factory:aas:CP-LAB-406`  
**Asset ID:** `urn:festo:cp-factory:asset:CP-LAB-406`  
**Fabricante:** Festo Didactic SE  
**Código de pedido:** CP-L-406-1  
**Artigo:** 8092834

### Submodelos do sistema

| Submodelo | ID | Descrição |
|-----------|-----|-----------|
| `Nameplate` | `urn:festo:cp-factory:sm:CP-LAB-406:Nameplate` | Placa de identificação do sistema (fabricante, artigo, código de pedido) |
| `TechnicalData` | `urn:festo:cp-factory:sm:CP-LAB-406:TechnicalData` | Dados técnicos gerais: tensão, pressão, dimensões, número de estações |
| `Hierarchy` | `urn:festo:cp-factory:sm:CP-LAB-406:Hierarchy` | Referências hierárquicas às 7 estações via `ReferenceElement` |
| `Documentation` | `urn:festo:cp-factory:sm:CP-LAB-406:Documentation` | Manual do sistema em PDF |
| `ProductionProcess` | `urn:festo:cp-factory:sm:CP-LAB-406:ProductionProcess` | Sequência completa de operações de produção por estação |
| `Maintenance` | `urn:festo:cp-factory:sm:CP-LAB-406:Maintenance` | Plano de manutenção preventiva e corretiva |

---

## Estações

### Estação 1 — MAGFRONT (Magazine Frente)
**Arquivo:** `station_magfront.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-MAGFRONT`  
**Função:** Alimentação de peças brutas na linha de produção. O magazine empilha as matérias-primas e injeta uma a uma nos portadores de pallete via cilindro pneumático.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2 (código CP-L-LINEAR-V2-C11M0, artigo D12501)
- Módulo: Festo CP-AM-MAG (magazine de alimentação)
- PLC: Siemens ET200SP CPU 1512SP F-1PN
- HMI: Siemens SIMATIC MTP700
- RFID: Siemens RF210R (IO-Link V1.1)

**Documentação:**
- [Manual do módulo MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/manual_en.pdf)
- [Esquemáticos MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/schematics.pdf)

---

### Estação 2 — MEAS (Medição)
**Arquivo:** `station_meas.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-MEAS`  
**Função:** Medição da altura da peça bruta para detectar cor/tipo e verificar conformidade dimensional. Sensores analógicos de deslocamento medem e classificam a peça.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2
- Módulo: Festo CP-AM-MEASURE-V2
- PLC: Siemens ET200SP CPU 1512SP F-1PN
- Sensor de medição: analógico por deslocamento (IO-Link)

**Documentação:**
- [Manual do módulo MEASURE V2](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/manual_en.pdf)
- [Esquemáticos MEASURE V2](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/schematics.pdf)
- [Label da tampa frontal](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MEASURE-V2/files/front_cover_label.pdf)

---

### Estação 3 — iDRILL (Furadeira Inteligente)
**Arquivo:** `station_idrill.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-iDRILL`  
**Função:** Furação CNC da tampa frontal quando requerida pela ordem de produção (peça No. 210). Fresa/furadeira controlada por servo com controle de força e posição.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2
- Módulo: Festo CP-AM-iDRILL
- PLC: Siemens ET200SP CPU 1512SP F-1PN
- Acionamento: servo motor com encoder

**Documentação:**
- [Manual do módulo iDRILL](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-iDRILL/files/manual_en.pdf)
- [Esquemáticos iDRILL](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-iDRILL/files/schematics.pdf)

---

### Estação 4 — MAGBACK (Magazine Trás)
**Arquivo:** `station_magback.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-MAGBACK`  
**Função:** Alimentação da tampa traseira (back cover) sobre a peça já posicionada no portador de pallete, preparando para a prensagem.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2
- Módulo: Festo CP-AM-MAG (magazine de alimentação — tampa traseira)
- PLC: Siemens ET200SP CPU 1512SP F-1PN

**Documentação:**
- [Manual do módulo MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/manual_en.pdf)
- [Esquemáticos MAG](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-MAG/files/schematics.pdf)

---

### Estação 5 — MPRESS (Prensa Pneumática)
**Arquivo:** `station_mpress.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-MPRESS`  
**Função:** Prensagem da tampa traseira sobre a tampa frontal utilizando músculo pneumático (fluidic muscle) com regulação de força. A força de prensagem é monitorada por sensor analógico.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2
- Módulo: Festo CP-AM-MPRESS (artigo 8038567)
- Atuador: músculo pneumático (fluidic muscle) + cilindro de fixação
- Sensor: força analógica + 2 sensores de posição do cilindro + sensor de peça presente
- PLC: Siemens ET200SP CPU 1512SP F-1PN

**Documentação:**
- [Manual do módulo PRESS](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-PRESS/files/manual_en.pdf)
- [Esquemáticos PRESS](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-PRESS/files/schematics.pdf)

---

### Estação 6 — OUT (Saída)
**Arquivo:** `station_out.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-OUT`  
**Função:** Retirada da peça acabada do portador de pallete e entrega ao operador ou sistema downstream. Pode incluir teste final e separação de peças OK/NOK.

**Equipamentos:**
- Esteira: Festo CP-L-LINEAR-V2
- Módulo: Festo CP-AM-OUT
- PLC: Siemens ET200SP CPU 1512SP F-1PN

**Documentação:**
- [Manual do módulo OUT](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-OUT/files/manual_en.pdf)
- [Esquemáticos OUT](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/CP-AM-OUT/files/schematics.pdf)

---

### Estação 7 — COBOT (Robô Colaborativo UR5e)
**Arquivo:** `station_cobot.json`  
**AAS ID:** `urn:festo:cp-factory:aas:STATION-COBOT`  
**Função:** Pick and place e operações de montagem colaborativas. O robô interage diretamente com os portadores de pallete da esteira, podendo realizar alimentação, montagem ou inspeção de peças.

**Equipamento:** Universal Robots UR5e (e-Series)

| Especificação | Valor |
|---------------|-------|
| Graus de liberdade | 6 |
| Payload máximo | 5 kg |
| Alcance | 850 mm |
| Repetibilidade | ± 0,03 mm |
| Velocidade TCP máx. | 1,0 m/s |
| Peso do braço | 20,6 kg |
| Alimentação | 100–240 VAC, 50/60 Hz |
| Consumo típico | 200 W |
| Controlador | CB5 (e-Series) |
| Segurança | PLd Cat.3 (ISO 13849) |
| Sensor F/T | 6 eixos integrado no pulso |

**Interfaces de comunicação:**
- Modbus TCP (porta 502)
- PROFINET IO (via URCap)
- EtherNet/IP
- OPC UA (porta 4840)
- RTDE — Real-Time Data Exchange (porta 30004)

**E/S do controlador CB5:**
- 8 entradas digitais (DI0–DI7)
- 8 saídas digitais (DO0–DO7)
- 2 entradas analógicas (AI0–AI1, 0–10V / 4–20mA)
- 2 saídas analógicas (AO0–AO1, 0–10V / 4–20mA)
- 8 entradas de segurança + 4 saídas de segurança

**E/S na flange da ferramenta:**
- 2 entradas digitais + 2 saídas digitais
- 2 entradas analógicas

**Documentação:**
- [Manual do usuário UR5e (EN) — SW5.19](https://www.universal-robots.com/manuals/EN/PDF/SW5_19/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf)
- [Manual do usuário UR5e (PT) — PolyScopeX SW10.12](https://www.universal-robots.com/manuals/pt/PDF/SW10_12/user-manual-UR5e-PolyX-PDF_online/718-749-00_UR5e%20PolyScope%20X_User_Manual_PolyScopeX_pt_Global.pdf)
- [Datasheet UR5e e-Series](https://www.universal-robots.com/media/1807465/ur5e_e-series_datasheets_web.pdf)
- [Fact Sheet UR5e (PT)](https://www.universal-robots.com/media/1820977/07_2021_ur5e_fact_sheet_pt_web.pdf)

---

## Submodelos por estação (estações 1–6)

Cada arquivo de estação (exceto COBOT) contém 8 submodelos:

| Submodelo | Prefixo de ID | Conteúdo |
|-----------|--------------|----------|
| `Conveyor_Nameplate` | `CP-L-LINEAR-V2-{STATION}` | Fabricante, artigo, código de pedido, número e papel da estação |
| `Conveyor_TechnicalData` | `CP-L-LINEAR-V2-{STATION}` | PLC (ET200SP), HMI (MTP700), RFID (RF210R), motor+encoder, pneumática, mapeamento de I/O |
| `Conveyor_Documentation` | `CP-L-LINEAR-V2-{STATION}` | Manual de operação e esquemáticos elétricos da esteira |
| `Module_Nameplate` | `CP-AM-{STATION}` | Fabricante, artigo, código de pedido do módulo de aplicação |
| `Module_TechnicalData` | `CP-AM-{STATION}` | Função, atuadores, sensores, dimensões, mapeamento de I/O do módulo |
| `Module_Documentation` | `CP-AM-{STATION}` | Manual e esquemáticos do módulo de aplicação |
| `IOInterface` | `STATION-{STATION}` | Todos os sinais de sensores e atuadores da esteira e do módulo com descrição bilíngue |
| `ProductionOrder` | `STATION-{STATION}` | Ordem MES ativa (ONo, OPos, operação, resource), peça no portador e catálogo de peças |

### Detalhes do `IOInterface`

Cada `IOInterface` é dividido em duas seções:

**`Conveyor`** — sinais da esteira CP-L-LINEAR-V2:
- *Sensors:* `BG1_CarrierPresence`, posições do stopper (BG21–BG24), `TF80_RFID_TagPresent`, `TF80_RFID_CarrierID`, `TF80_RFID_StateCode`
- *Actuators:* `MB20_BeltMotor`, `Y1_StopperCylinder`

**`Module`** — sinais específicos de cada módulo de aplicação (varia por estação):
- *MAG:* presença de peça, cilindro ejetor, sensor de magazine vazio
- *MEAS:* sensor de deslocamento analógico, resultado de medição
- *iDRILL:* posição do spindle, força de furação, sensor de peça
- *MPRESS:* posição do cilindro (cima/baixo), presença de tampa traseira, força de prensagem, músculo pneumático, cilindro de fixação
- *OUT:* sensor de peça presente, cilindro de saída

### Detalhes do `ProductionOrder`

| Coleção | Propriedades |
|---------|-------------|
| `CurrentOrder` | `OrderNumber` (ONo), `OrderPosition` (OPos), `OperationNumber`, `OperationName`, `Resource`, `CarrierID`, `StateCode`, `Parameter1`–`Parameter4` |
| `CurrentWorkpiece` | `PartNumber` (PNo), `PartDescription`, `QualityResult` |
| `WorkpieceCatalog` | Todas as peças possíveis naquela estação com número, descrição em EN e PT |

---

## Catálogo de peças (WorkpieceCatalog)

| Nº | Descrição (EN) | Descrição (PT) |
|----|----------------|----------------|
| 101 | CP raw material black | CP matéria-prima preta |
| 102 | CP raw material grey | CP matéria-prima cinza |
| 103 | CP raw material blue | CP matéria-prima azul |
| 104 | CP raw material red | CP matéria-prima vermelha |
| 107 | CP front cover red | CP tampa frontal vermelha |
| 108 | CP front cover blue | CP tampa frontal azul |
| 109 | CP front cover grey | CP tampa frontal cinza |
| 110 | CP front cover black (No. 110) | CP tampa frontal preta |
| 111 | CP back cover black (No. 111) | CP tampa traseira preta |
| 210 | CP front cover black with CNC hole (No. 210) | CP tampa frontal preta com furo CNC |
| 1200 | CP black complete without board (No. 1200) | CP preto completo sem placa |

---

## Esquema de identificadores (URNs)

```
Sistema
  AAS:    urn:festo:cp-factory:aas:CP-LAB-406
  Asset:  urn:festo:cp-factory:asset:CP-LAB-406
  SM:     urn:festo:cp-factory:sm:CP-LAB-406:{SubmodelName}

Estações
  AAS:    urn:festo:cp-factory:aas:STATION-{NAME}
  Asset:  urn:festo:cp-factory:asset:STATION-{NAME}

Submodelos da esteira
  SM:     urn:festo:cp-factory:sm:CP-L-LINEAR-V2-{STATION}:{SubmodelName}

Submodelos do módulo de aplicação
  SM:     urn:festo:cp-factory:sm:CP-AM-{STATION}:{SubmodelName}

Submodelos IOInterface e ProductionOrder
  SM:     urn:festo:cp-factory:sm:STATION-{STATION}:{SubmodelName}

Submodelos do COBOT UR5e
  SM:     urn:festo:cp-factory:sm:UR5e-COBOT:{SubmodelName}
```

Nomes usados para `{NAME}` / `{STATION}`:

| Estação | Nome |
|---------|------|
| Magazine frente | `MAGFRONT` |
| Medição | `MEAS` |
| Furadeira | `iDRILL` |
| Magazine trás | `MAGBACK` |
| Prensa | `MPRESS` |
| Saída | `OUT` |
| Cobot | `COBOT` |

---

## Conformidade AAS V3

Todos os arquivos seguem a especificação **IEC 63278 Parte 2 v3.0**:

- `modelType` presente em todos os elementos (AAS, Submodel, Property, File, SubmodelElementCollection, ReferenceElement)
- `SubmodelElementCollection.value` — chave correta (não `submodelElements`)
- `File.contentType` — chave correta (não `mimeType`)
- `globalAssetId` como string simples
- `ExternalReference` e `ModelReference` com tipagem explícita
- Descrições bilíngues (`en` + `pt`) em todos os submodelos e propriedades
- `conceptDescriptions: []` presente em todos os arquivos JSON
- `defaultThumbnail` com `path` e `contentType` em todos os AAS de estação

---

## Manutenção

Manual de manutenção comum a todas as estações Festo:  
[CP Factory Maintenance Manual 2023](https://ip.festo-didactic.com/Infoportal/CPFactoryLab/data/common/files/CP-Maintenance_Manual-2023.07-en.pdf)
