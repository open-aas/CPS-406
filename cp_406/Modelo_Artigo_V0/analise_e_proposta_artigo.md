# Análise do Artigo Base e Proposta para Novo Artigo — CPS-406 + Faaster

> Gerado em: 2026-05-28  
> Baseado em: `tesis_final.tex` (Modelo_Artigo_V0) + contexto do projeto CPS-406

---

## PARTE 1 — Extração Completa do Artigo Atual

### Título e Autoria

**"Development of a Novel Retrofit Framework Considering Industry 4.0 Concepts: A Case Study of a Didactic Manufacture Production System"**

- **Autores:** Rafael da Silva Mendonça, Renan Landau Paiva de Medeiros, Vicente Ferreira de Lucena Jr.
- **Instituição:** UFAM / Samsung SUPER (acordo Samsung-UFAM, Decreto n°10.521/2020)
- **Financiamento:** FAPEAM, CAPES, CNPq, UFAM
- **Formato:** IEEE Journal (IEEEtran)

---

### 1.1 Palavras-chave

`methodology`, `retrofitting`, `legacy system`, `digital twin`, `RAMI 4.0`, `smart factory criteria`

---

### 1.2 Problema Central

- Sistemas legados obsoletos sem compatibilidade com I4.0
- Falhas de interoperabilidade, segurança, manutenção e desempenho
- Custo elevado de substituição total vs. atualização seletiva (retrofit)
- Ausência de metodologia estruturada para retrofit orientado a Digital Twin

---

### 1.3 Conceitos-Chave Tratados

| Tema | Detalhamento no artigo |
|---|---|
| **Digital Twin (DT)** | Réplica virtual do sistema físico com sincronização em tempo real |
| **Retrofitting** | Processo estruturado de atualização de sistemas legados |
| **RAMI 4.0** | Modelo de referência para avaliação de maturidade I4.0 |
| **CPS (Cyber-Physical System)** | Integração física-virtual com 5 camadas (L0–L4) |
| **IoT** | Sensores e dispositivos conectados em rede |
| **OPC UA** | Protocolo via EasyPort/EZOPC para comunicação OPC |
| **CANopen** | Protocolo de rede industrial para integração de módulos |
| **Smart Factory** | Critérios F1–F5 de avaliação de fábricas inteligentes |
| **MPS Festo** | Plataforma modular didática com módulos M1–M5 |
| **CIROS** | Software de simulação e DT proprietário da Festo |
| **Cloud Computing** | Mencionado como tecnologia I4.0 (não implementado) |
| **Big Data** | Mencionado como tecnologia I4.0 (não implementado) |

---

### 1.4 Metodologia — 5 Passos do Framework Retrofit

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1 — Levantamento e limitações operacionais        │
│           Diagnóstico completo do sistema legado        │
├─────────────────────────────────────────────────────────┤
│  STEP 2 — Definição de objetivos                        │
│           Metas de atualização, custos, benefícios      │
├─────────────────────────────────────────────────────────┤
│  STEP 3 — Seleção de componentes e tecnologias          │
│           Priorização por impacto, custo, complexidade  │
├─────────────────────────────────────────────────────────┤
│  STEP 4 — Integração dos novos componentes              │
│           Compatibilidade, plano de integração, testes  │
├─────────────────────────────────────────────────────────┤
│  STEP 5 — Testes e validação                            │
│           Manual + automatizado, ciclos operacionais    │
└─────────────────────────────────────────────────────────┘
```

---

### 1.5 Arquitetura DT — 5 Camadas (baseada em RAMI 4.0)

| Camada | Nome | Função |
|---|---|---|
| **L0** | Physical Layer | Sensores, atuadores, conveyors, braço robótico |
| **L1** | Data Layer | Coleta, filtragem e classificação de dados |
| **L2** | Integration Layer | IoT, interoperabilidade entre camadas |
| **L3** | Service Layer | DT services: monitoramento, diagnóstico, prognóstico, IA |
| **L4** | Decision Layer | Controle de metas, manutenção preditiva, scripts |

---

### 1.6 Caso de Estudo — MPS Festo (plataforma didática)

#### Módulos e Status

| Módulo | Nome | Status diagnosticado |
|---|---|---|
| **M1** | Transporter (Handling) | Sensor óptico solto, fibra deteriorada, driver elétrico parcial |
| **M2** | Press | Mangueiras deterioradas, pistão desalinhado |
| **M3** | Capper (Pick & Place) | Canvas rasgado, suction cup desgastada, sem painel |
| **M4** | Robotic Arm | Sem home position, hoses deterioradas, não inicializa |
| **M5** | Parts Storage | Bom estado — estoque de saída de peças |

#### Stack Tecnológica do Artigo

**Hardware legado identificado:**
- CPX-E-CEC-C1 (controlador antigo)
- Fieldbus interface (protocolo legado)
- DC motor controller (não funcionando)
- I/O data cable SysLink, fio paralelo
- Router D-LINK DI-524/150 wireless
- Software: Codesys, Ciros (sem licença)

**Hardware atualizado:**
- CPU **CPX-CEC-C1-V3** (novo controlador Festo)
- Switch TP-Link 8 portas
- I/O Link / CANopen
- Fieldbus node CTEU CANopen
- PS control console para SysLink
- DC motor controller (novo)
- I/O data cable crossover com socket FBA-2-M12-5POL
- Access Point DIR-842
- **CODESYS V3**, **CIROS 7** e MES com licenças

**Stack de comunicação:**
```
MPS (hardware físico)
  └── EasyPort (interface USB → OPC)
        └── EZOPC (OPC Server)
              └── CIROS Education (OPC Client / Digital Twin)
```

---

### 1.7 Avaliação de Maturidade RAMI — Critérios Smart Factory

| Critério | Sistema Legado | Sistema Atualizado | Variação |
|---|:---:|:---:|:---:|
| **F1** — Automação de Processos | Nível 3 | Nível 4 | **+1** |
| **F2** — Integração de Sistemas | Nível 2 | Nível 4 | **+2** |
| **F3** — Uso de Dispositivos Inteligentes | Nível 1 | Nível 3 | **+2** |
| **F4** — Análise de Dados em Tempo Real | Nível 1 | Nível 4 | **+3** |
| **F5** — Flexibilidade de Produção | Nível 2 | Nível 3 | **+1** |

---

### 1.8 Contribuições Declaradas no Artigo Base

1. Framework de retrofit em 5 passos — replicável para qualquer sistema legado
2. Aplicação de DT em sistema didático real como validação do framework
3. Avaliação de maturidade antes/depois com critérios RAMI 4.0
4. Metodologia qualitativa + quantitativa integrada para avaliação de smart factories

---

### 1.9 Lacunas e Limitações do Artigo Base

| Limitação | Impacto |
|---|---|
| Usa CIROS (proprietário Festo) | Sem abertura, sem interoperabilidade com outros sistemas |
| Não usa AAS (Asset Administration Shell) | Sem modelo de dados padronizado ISO/IEC 63278 |
| OPC via EasyPort, não OPC UA nativo | Limitado à plataforma Festo, protocolo legado |
| Sem HDA (Historical Data Access) | Sem registro histórico de processo para análise |
| Sem semântica (semantic IDs, ontologia) | Dados não são interpretáveis por máquinas externas |
| Sem edge computing ou cloud | Processamento apenas local |
| M4 (robô) não funcionando durante estudo | Caso de estudo incompleto — 3 módulos efetivos |
| Sem integração com robô colaborativo | Ausência de cobot no processo |
| Sem métricas OEE, MTBF, MTTR reais | Avaliação de maturidade subjetiva, sem evidências quantitativas |
| Avaliação RAMI é qualitativa | Sem instrumentos de medição objetivos |

---

## PARTE 2 — Proposta para Novo Artigo: CPS-406 + Faaster

### 2.1 Títulos Sugeridos

**Opção 1 — Foco em AAS + OPC UA:**
> *"AAS-Driven Digital Twins for Modular Manufacturing: A Standards-Based Approach Using Faaster OPC UA Runtime on the Festo CP-406 Factory"*

**Opção 2 — Foco em automação do DT:**
> *"From AAS V3 to Live OPC UA: Automated Digital Twin Generation for Each Module of the CP-406 Didactic Production System Using Faaster"*

**Opção 3 — Foco em interoperabilidade:**
> *"Towards Interoperable Digital Twins in Industry 4.0: Asset Administration Shell V3 and OPC UA Integration via Faaster on the CP-406 Modular Plant"*

**Opção 4 — Foco em framework genérico:**
> *"A Generic AAS-to-OPC-UA Framework for Per-Module Digital Twin Generation: Design, Implementation and Evaluation on a Seven-Station Modular Manufacturing System"*

---

### 2.2 Diferencial Científico em Relação ao Artigo Base

| Aspecto | Artigo Base (MPS Festo) | Artigo Proposto (CPS-406 + Faaster) |
|---|---|---|
| Padrão de modelo de dados | Proprietário (CIROS/Festo) | **AAS V3 (IEC 63278)** — padrão aberto ISO/IEC |
| Protocolo de comunicação | OPC legado (EasyPort/EZOPC) | **OPC UA (IEC 62541)** nativo |
| Granularidade do DT | Sistema inteiro (monolítico) | **Por módulo** — 7 AAS individuais + 1 AAS sistema |
| Semântica dos dados | Ausente | **Semantic IDs, ECLASS, IRI padronizados** |
| Dados históricos | Ausente | **HDA via TimescaleDB** |
| Automação do DT | Manual (configurar CIROS) | **Automática** (Faaster lê AAS JSON → OPC UA) |
| Robótica colaborativa | Ausente | **UR5e Cobot (Estação 7)** |
| Hierarquia sistêmica | Implícita, não modelada | **Hierarquia explícita CP-LAB-406 → 7 estações** |
| Escalabilidade | Limitada à plataforma Festo | **Framework genérico replicável** |
| Reprodutibilidade | Não disponível | **Repositório aberto GitHub + Zenodo** |
| Validação experimental | Qualitativa (RAMI subjetivo) | **Métricas quantitativas: latência, OEE, fidelidade** |
| N° de módulos | 3–4 módulos MPS | **7 estações CPS-406** |

---

### 2.3 Estrutura Proposta para o Novo Artigo

---

#### Seção 1 — Introdução

**Temas a explorar:**

- A limitação das abordagens proprietárias de DT (CIROS, Siemens NX, Dassault 3DExperience)
- A emergência do AAS como padrão ISO/IEC para interoperabilidade em I4.0
- O papel do OPC UA como protocolo de facto para comunicação industrial
- A lacuna entre especificação AAS estática (JSON) e execução como servidor OPC UA vivo
- O Faaster como ponte entre arquivo JSON estático e runtime dinâmico
- Motivação: CPS-406 como sistema real de manufatura modular com 7 estações heterogêneas (PLCs, sensores, Cobot UR5e)

**Argumentação de impacto:**
- Quantos sistemas legados existem no Brasil/mundo sem DT padronizado
- Custo de implementação proprietária vs. abordagem AAS open-source
- Importância do contexto didático para formação de engenheiros I4.0

**Citações-chave a buscar:**
- IEC 63278 Parts 1, 2, 3 (AAS standard)
- IEC 62541 (OPC UA standard)
- Platform Industrie 4.0 whitepapers (ZVEI, VDI, BITKOM)
- IDTA (Industrial Digital Twin Association) — submodel templates
- Grieves (2014) — origem conceitual do Digital Twin
- Kritzinger et al. (2018) — taxonomia de DT (Digital Model, Shadow, Twin)

---

#### Seção 2 — Background / Revisão da Literatura

**Temas a cobrir:**

- **AAS V3:** estrutura completa (AssetAdministrationShell, Submodel, SME types, semantic IDs, PathType, qualifiers)
- **OPC UA:** address space, nodes, Type 1 (passive) vs. Type 2 (reactive) servers, subscriptions, HDA
- **Digital Twin:** definições, taxonomias, graus de sincronização
- **Retrofit vs. Greenfield DT:** diferenças de abordagem, custos, benefícios
- **Padrões de interoperabilidade:** RAMI 4.0, IEC 62890, ISA-95, IEC 61131-3
- **Plataformas abertas de AAS:** FA³ST (Fraunhofer), Eclipse BaSyx, AASX Package Explorer

**Tabela comparativa crítica para incluir:**

| Ferramenta | AAS V3 | OPC UA | HDA | Multi-módulo | Open Source | Auto-geração |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| CIROS (Festo) | Não | OPC legado | Não | Sim (prop.) | Não | Não |
| FA³ST (Fraunhofer) | Sim | Sim | Não | Limitado | Sim | Parcial |
| Eclipse BaSyx | Sim | Parcial | Não | Sim | Sim | Não |
| AASX Package Explorer | Sim | Não | Não | Sim | Sim | Não |
| **Faaster** | **Sim** | **Sim** | **Sim** | **Sim (7)** | **Sim** | **Sim** |

---

#### Seção 3 — O Sistema CP-406 (Caso de Estudo)

**Temas:**
- Descrição física detalhada de cada estação
- Topologia de comunicação por módulo (PLC, sensores, atuadores, protocolos)
- Processo produtivo completo: peça entra em MAGFRONT → processa nas estações → sai em OUT com COBOT
- Integrações nativas: I/O digital, OPC UA dos PLCs Festo CP Factory
- Características do UR5e (Estação 7): ROS, URScript, OPC UA server nativo Universal Robots
- Diagrama de fluxo do processo de manufatura

**Tabela das 7 Estações:**

| # | Arquivo AAS | Módulo Físico | AAS ID |
|---|---|---|---|
| 1 | `station_magfront.json` | CP-AM-MAG (entrada) | `urn:festo:cp-factory:aas:STATION-MAGFRONT` |
| 2 | `station_meas.json` | CP-AM-MEASURE-V2 | `urn:festo:cp-factory:aas:STATION-MEAS` |
| 3 | `station_idrill.json` | CP-AM-iDRILL | `urn:festo:cp-factory:aas:STATION-iDRILL` |
| 4 | `station_magback.json` | CP-AM-MAG (saída) | `urn:festo:cp-factory:aas:STATION-MAGBACK` |
| 5 | `station_mpress.json` | CP-AM-MPRESS | `urn:festo:cp-factory:aas:STATION-MPRESS` |
| 6 | `station_out.json` | CP-AM-OUT | `urn:festo:cp-factory:aas:STATION-OUT` |
| 7 | `station_cobot.json` | Universal Robots UR5e | `urn:festo:cp-factory:aas:STATION-COBOT` |
| — | `cp_lab_406_system.json` | Sistema CP-LAB-406 | `urn:festo:cp-factory:aas:CP-LAB-406` |

---

#### Seção 4 — Modelagem em AAS V3 por Módulo

**Temas:**

- Estrutura hierárquica: AAS Sistema → 7 AAS de estação
- Submodelos implementados por estação:
  - **Nameplate** — identificação, fabricante, número de série, versão
  - **TechnicalData** — tensão, corrente, ciclo de produção, parâmetros físicos
  - **Documentation** — manuais PDF, links, thumbnails (URL HTTPS)
  - **IOInterface** — entradas/saídas digitais e analógicas com semantic IDs
  - **ProductionOrder** — script de produção, parâmetros configuráveis
- Uso de Semantic IDs (ECLASS, IRIs padronizados)
- PathType para thumbnails — validação de URL HTTPS no metamodel
- Validação de schema AAS V3 (metamodel Python integrado ao Faaster)

**Problema técnico e solução (patch PathType):**

O validador `path_type.py` do Faaster não aceita URLs HTTPS por padrão. A solução é adicionar a regex HTTPS como primeira alternativa:

```python
# Antes (não aceita HTTPS):
FILE_URI_REGEX = re.compile(
    r"^(?:"
    r"/.*|"
    r"\.{1,2}/.*|"
    ...
    r")\Z"
)

# Depois (aceita HTTPS):
FILE_URI_REGEX = re.compile(
    r"^(?:"
    r"https?://[^\s]+|"   # primeira alternativa adicionada
    r"/.*|"
    r"\.{1,2}/.*|"
    ...
    r")\Z"
)
```

**Contribuição técnica desta seção:**
- 7 arquivos JSON AAS V3 completos e validados, disponibilizados em repositório aberto
- 1 arquivo AAS de sistema (hierarquia)
- Script Python de validação automática dos 8 arquivos

---

#### Seção 5 — Faaster: Runtime OPC UA para AAS

**Temas:**

- Arquitetura interna do Faaster
- Pipeline de transformação: `AAS JSON → Parser → OPC UA Nodes → TimescaleDB`
- Mapeamento de tipos AAS → OPC UA:

| Tipo AAS | Tipo OPC UA |
|---|---|
| `Property` | `Variable` |
| `SubmodelElementCollection` | `Object` |
| `Operation` | `Method` |
| `ReferenceElement` | `Reference` |
| `File` / `Blob` | `Variable` (URI) |
| `AnnotatedRelationshipElement` | `HasComponent` reference |

- Servidor OPC UA reativo Type 2 (push de dados do físico em tempo real)
- HDA: queries de séries temporais por `idShort` via TimescaleDB
- Integrações de transporte suportadas: MQTT, Modbus, BLE (heterogeneidade entre estações)
- Namespaces OPC UA por AAS (isolamento entre estações)
- Auto-discovery: cliente OPC UA pode enumerar todos os nós gerados

**Arquitetura do Faaster:**

```
faaster/
├── aas_metamodel/       # Metamodel AAS V3 + validadores schema
│   └── models/
│       └── path_type.py # Validador PathType (patch HTTPS necessário)
├── parser/              # Parser AAS JSON → nós OPC UA
├── opcua_server/        # Servidor OPC UA reativo Type 2
├── hda/                 # Historical Data Access via TimescaleDB
└── models/              # JSONs AAS do CPS-406 (entrada)
```

---

#### Seção 6 — Implementação e Integração

**Temas:**

- Deploy do Faaster para cada AAS de estação (containerizado Docker)
- Configuração OPC UA por módulo: endpoint, porta, namespace, security
- Sincronização com PLCs Festo CP Factory via Modbus/OPC UA
- Sincronização com UR5e via OPC UA nativo (servidor embutido Universal Robots)
- Dashboard de monitoramento: Grafana + TimescaleDB + visualização em tempo real
- Demonstração de live data: sensores físicos atualizando DT
- Topologia de rede do sistema completo (diagrama)

**Stack tecnológica do novo artigo:**

```
CPS-406 (hardware físico, 7 estações)
  ├── PLCs Festo CP Factory (Modbus/OPC UA)
  ├── Sensores: indutivos, capacitivos, ópticos, câmera
  ├── Atuadores: pneumáticos, esteiras, prensas
  └── UR5e Cobot (OPC UA nativo)
       │
       ▼ Faaster (runtime Python)
  ├── Parser AAS V3 JSON
  ├── OPC UA Server Type 2 (asyncua / python-opcua)
  ├── TimescaleDB (HDA)
  └── REST API (opicional)
       │
       ▼ Clientes
  ├── UaExpert (inspeção manual)
  ├── Node-RED (dashboard)
  ├── Grafana (visualização histórica)
  └── Qualquer cliente OPC UA padrão
```

---

#### Seção 7 — Avaliação / Resultados

> Esta é a seção mais crítica para aceitação em Qualis A. Veja Parte 3 para métricas detalhadas.

**Estrutura sugerida de resultados:**

- **7.1** Avaliação de maturidade RAMI — por módulo, antes/depois (tabela e spider chart)
- **7.2** Latência de sincronização do DT — por estação, N=100 amostras
- **7.3** Fidelidade do modelo — RMSE e MAE por sensor, por módulo
- **7.4** Escalabilidade do Faaster — 1 a 7 estações simultâneas
- **7.5** OEE com e sem DT — comparativo de downtime, MTTR, throughput
- **7.6** Interoperabilidade — teste com 3 clientes OPC UA distintos

---

#### Seção 8 — Discussão

**Temas:**

- Contribuição do AAS padronizado vs. modelo proprietário (análise crítica)
- Limitações identificadas: latência de rede, overhead de serialização JSON, escala
- Generalização: o Faaster pode ser aplicado a qualquer AAS V3 (não apenas CPS-406)
- Impacto educacional: laboratório didático como plataforma de pesquisa I4.0
- Trabalhos futuros: IA/ML para manutenção preditiva com dados HDA, cloud deployment, federação de DTs

---

#### Seção 9 — Conclusão

- Reafirmação da contribuição principal: framework AAS V3 → OPC UA automático por módulo
- 7 modelos AAS completos e validados disponibilizados publicamente
- Faaster como runtime genérico e replicável
- Impacto para pesquisa e ensino de I4.0
- Repositório aberto: GitHub (open-aas/CPS-406) + Zenodo com DOI

---

## PARTE 3 — Métricas para Artigo Qualis A

### 3.1 Journals-Alvo e Classificação

| Journal | Impact Factor | Qualis BR | Afinidade |
|---|:---:|:---:|---|
| **IEEE Transactions on Industrial Informatics** | ~12.3 | A1 | I4.0, DT, OPC UA — core scope |
| **Robotics & Computer-Integrated Manufacturing** | ~10.4 | A1 | Cobot UR5e + CPS integrado |
| **Journal of Manufacturing Systems** | ~9.1 | A1 | Sistema modular de manufatura |
| **Computers & Industrial Engineering** | ~7.9 | A1 | Retrofit + AAS aplicado |
| **IEEE Transactions on Industrial Electronics** | ~8.2 | A1 | Eletrônica industrial, sensores |
| **IEEE Access** | ~3.4 | A2 | Open access, rápido, casos de estudo |
| **Int'l Journal of Advanced Manufacturing Technology** | ~3.5 | A2 | Tecnologia de manufatura aplicada |
| **Journal of Intelligent Manufacturing** | ~8.0 | A1 | IA + manufatura + DT |

---

### 3.2 Métricas Quantitativas (Hard Metrics)

#### A. Métricas de Desempenho do Digital Twin

| Métrica | Definição | Fórmula / Como Medir |
|---|---|---|
| **Latência de Sincronização (LS)** | Tempo entre evento físico e atualização no DT | Timestamp PLC vs. timestamp nó OPC UA (ms) |
| **Taxa de Atualização (TA)** | Frequência de refresh do DT | Publicações OPC UA / segundo (Hz) |
| **Fidelidade do Modelo (FM)** | Desvio percentual entre valor real e DT | `(|v_físico - v_DT| / v_físico) × 100` |
| **RMSE do DT** | Erro quadrático médio por sensor | `√(Σ(v_físico - v_DT)² / N)` |
| **MAE do DT** | Erro absoluto médio por sensor | `Σ|v_físico - v_DT| / N` |
| **Disponibilidade do DT** | Uptime do servidor Faaster/OPC UA | `t_operação / t_total × 100` (%) |
| **Throughput de Dados** | Volume transmitido por ciclo de produção | KB/ciclo (Wireshark/tcpdump) |

#### B. Métricas de Qualidade do Modelo AAS

| Métrica | Definição | Fórmula |
|---|---|---|
| **Completude do Modelo (CM)** | % de propriedades físicas modeladas no AAS | `props_modeladas / props_totais × 100` |
| **Conformidade Semântica (CS)** | % de SMEs com semantic ID válido | `SMEs_com_ID / SMEs_totais × 100` |
| **Taxa de Validação (TV)** | % de arquivos AAS sem erros de schema | `AAS_válidos / AAS_total × 100` |
| **Cobertura de Submodelos** | N° de submodelos por estação | Contagem (de 5 possíveis: Nameplate, TechData, Doc, IO, ProdOrder) |
| **Density de Nós OPC UA** | Nós gerados por propriedade AAS | `N°_nós / N°_props` |

#### C. Métricas de Produção (OEE — Overall Equipment Effectiveness)

| Métrica | Fórmula | Aplicação no CPS-406 |
|---|---|---|
| **OEE Global** | `Disponibilidade × Desempenho × Qualidade` | OEE do sistema CP-LAB-406 completo |
| **OEE por Estação** | Idem, por módulo | MAGFRONT, iDRILL, MPRESS, OUT, COBOT |
| **Disponibilidade** | `t_produção_real / t_planejado` | Por estação, extraído do DT |
| **Desempenho** | `peças_produzidas / peças_teóricas` | Taxa de ciclo real vs. nominal |
| **Qualidade** | `peças_boas / peças_total` | Peças aprovadas / total processado |
| **Cycle Time** | Tempo médio de processamento por peça | Timestamps OPC UA entre entrada e saída de cada estação |
| **Throughput** | Peças/hora do sistema completo | Dados do DT em tempo real via HDA |
| **MTBF** | Mean Time Between Failures | `t_total / N°_falhas` — histórico TimescaleDB |
| **MTTR** | Mean Time To Repair | Tempo médio de reparo registrado no DT |

#### D. Métricas de Comunicação OPC UA

| Métrica | Definição |
|---|---|
| **Latência OPC UA (LOU)** | RTT de request/response (ms) — por estação |
| **Jitter** | Desvio padrão da latência (ms) — estabilidade do protocolo |
| **Nodes no Address Space** | N° de nós OPC UA gerados por AAS |
| **Taxa de Erro de Subscrição** | % publicações OPC UA perdidas / total enviadas |
| **Overhead do Protocolo** | Bytes de overhead OPC UA / bytes de dados úteis |
| **Concurrent Subscriptions** | N° máximo de clientes simultâneos sem degradação |

#### E. Métricas de Escalabilidade do Faaster

| Métrica | Experimento |
|---|---|
| **CPU% por N estações** | Executar 1, 3, 5, 7 AAS simultâneos → medir CPU |
| **RAM por N estações** | Idem → medir memória RSS |
| **Latência vs. N estações** | Latência OPC UA com carga crescente |
| **Throughput vs. N estações** | Publicações/s com 1 a 7 AAS ativos |
| **Tempo de inicialização** | Segundos para Faaster parsear e expor 1/7 AAS |

#### F. Métricas de Maturidade RAMI — Quantificadas

Substituir avaliação subjetiva do artigo base por scoring mensurável:

| Critério RAMI | Indicador Quantitativo Proposto |
|---|---|
| **F1 — Automação** | % de ações manuais eliminadas após implantação do DT |
| **F2 — Integração** | N° sistemas integrados via OPC UA / N° sistemas totais |
| **F3 — Dispositivos Inteligentes** | N° sensores com semantic ID / N° total de sensores |
| **F4 — Análise de Dados** | GB de dados históricos acessíveis via HDA por mês |
| **F5 — Flexibilidade** | N° configurações de produção testadas no DT sem parar planta |

---

### 3.3 Métricas Qualitativas (Soft Metrics)

| Métrica | Instrumento de Medição |
|---|---|
| **Usabilidade do DT** | System Usability Scale (SUS, Brooke 1996) — 10 itens, score 0–100 |
| **Facilidade de Manutenção** | MTTR estimado por operador com DT vs. sem DT (comparativo subjetivo) |
| **Replicabilidade** | Outro grupo consegue criar AAS para nova estação em < X horas? (experimento) |
| **Conformidade com Padrões** | Checklist IEC 63278 Parts 1, 2, 3 — % requisitos atendidos |
| **Percepção de Interoperabilidade** | Questionário Likert 1–5 com operadores e desenvolvedores |
| **Facilidade de Integração** | N° linhas de configuração necessárias para adicionar nova estação |

---

### 3.4 Experimentos para Validação Experimental

> Experimentos quantitativos são obrigatórios para aceitação em journals IEEE/Qualis A.

#### Experimento 1 — Benchmark de Latência por Módulo

```
Protocolo:
1. Gerar evento físico em cada estação (ex.: sensor detecta peça)
2. Medir timestamp no PLC (t0)
3. Medir timestamp no cliente OPC UA ao receber atualização (t1)
4. LS = t1 - t0
5. Repetir N=100 vezes por estação

Resultados esperados:
- Tabela: média ± desvio padrão, p95, p99 por módulo
- Gráfico boxplot por estação
- CDF (Cumulative Distribution Function) da latência
```

#### Experimento 2 — Validação de Fidelidade do Modelo

```
Protocolo:
1. Ler valor do sensor físico diretamente (ground truth)
2. Ler valor do mesmo sensor via DT (nó OPC UA)
3. Calcular RMSE e MAE por sensor
4. Repetir durante 1 ciclo completo de produção (todas as 7 estações)

Resultados esperados:
- RMSE e MAE por tipo de sensor (indutivo, óptico, analógico)
- Tabela de fidelidade por módulo
```

#### Experimento 3 — Escalabilidade do Faaster

```
Protocolo:
1. Executar Faaster com 1 AAS ativo
2. Medir: CPU%, RAM, latência OPC UA, throughput durante 5 minutos
3. Adicionar AAS até 7 simultâneos
4. Plotar curvas de escalabilidade

Resultados esperados:
- Gráficos de CPU/RAM/latência vs. N estações ativas
- Identificação do ponto de saturação
```

#### Experimento 4 — OEE com vs. sem DT (comparativo longitudinal)

```
Protocolo:
- Período A (2 semanas): produção sem DT → monitoramento manual
- Período B (2 semanas): produção com Faaster ativo → monitoramento automático

Métricas comparadas:
- Tempo médio de detecção de falha (MTTD)
- MTTR (Mean Time To Repair)
- Downtime total por período
- OEE global

Resultados esperados:
- Tabela comparativa A vs. B
- % de melhoria em cada métrica
```

#### Experimento 5 — Interoperabilidade com Clientes OPC UA Externos

```
Protocolo:
1. Subir Faaster com 7 AAS do CPS-406
2. Conectar com 3 clientes OPC UA distintos:
   - UaExpert (Unified Automation) — inspeção manual
   - Node-RED (dashboard industrial)
   - Python opcua-asyncio (client programático)
3. Validar que todos leem todos os nós corretamente
4. Opicional: OPC Foundation CTT (Compliance Test Tool)

Resultados esperados:
- Tabela de compatibilidade: cliente × funcionalidade OPC UA
- Evidências de screenshot/log de cada cliente
```

#### Experimento 6 — Tempo de Modelagem AAS por Módulo

```
Protocolo:
- Registrar tempo gasto para modelar cada estação em AAS V3
- Medir com e sem template/ferramenta auxiliar

Resultados esperados:
- Curva de aprendizado (estação 1 vs. estação 7)
- Estimativa de esforço para replicar a outros sistemas
```

---

### 3.5 Elementos Obrigatórios para Revisão Qualis A

| Elemento | Detalhamento |
|---|---|
| **Revisão de literatura** | Mínimo 40 referências, incluindo IEEE/ACM/Elsevier de 2020–2025 |
| **Validação experimental** | N estatisticamente significativo (mínimo N=30 por experimento) |
| **Análise estatística** | Média, desvio padrão, intervalos de confiança 95%, testes t ou ANOVA |
| **Comparação com estado da arte** | Tabela comparando Faaster com FA³ST, BaSyx, CIROS em métricas objetivas |
| **Reprodutibilidade** | Código e dados disponíveis publicamente (GitHub + Zenodo) |
| **Figuras de alta qualidade** | Arquitetura, fluxogramas, gráficos vetoriais (PDF/SVG) |
| **Tabelas comparativas** | AAS por estação, métricas RAMI, resultados de experimentos |
| **Limitações declaradas** | Seção de discussão honesta — revisores exigem autocrítica |
| **Trabalhos futuros concretos** | Ex.: "Integrar ML para manutenção preditiva usando HDA do módulo iDRILL" |
| **Dataset público** | Série temporal dos sensores do CPS-406 no Zenodo ou Harvard Dataverse |
| **DOI para dados** | Repositório com DOI aumenta citações e credibilidade |

---

### 3.6 Métricas de Impacto Acadêmico (Posicionamento do Artigo)

| Estratégia | Justificativa |
|---|---|
| **Repositório aberto** | 7 AAS JSON no GitHub com DOI via Zenodo — cria citabilidade dos dados |
| **Docker-compose funcional** | Faaster + TimescaleDB + exemplo completo — demonstra reprodutibilidade |
| **Dataset público** | Série temporal de sensores do CPS-406 — Zenodo, Harvard Dataverse |
| **Comparação quantitativa** | Tabela Faaster vs. FA³ST vs. BaSyx em métricas objetivas |
| **N° de submodelos** | 5 submodelos × 7 estações = 35 submodelos — contribuição robusta |
| **Cobertura de estações** | Todos os 7 módulos + sistema = diferencial sobre artigos de caso único |
| **Cobot integrado** | UR5e com OPC UA nativo — diferencial raro em literatura didática |

---

## PARTE 4 — Diagrama de Posicionamento

```
Artigo Base (Mendonça et al.)              Artigo Proposto (CPS-406 + Faaster)
──────────────────────────────             ──────────────────────────────────────
Framework Retrofit (5 passos)       →      Framework AAS-Driven DT (7 módulos)
CIROS proprietário Festo            →      Faaster open-source Python
OPC legado (EasyPort/EZOPC)         →      OPC UA nativo (IEC 62541)
Sem modelo de dados padrão          →      AAS V3 (IEC 63278) completo e validado
Avaliação RAMI qualitativa          →      Métricas quantitativas por módulo
3 módulos MPS ativos                →      7 estações CPS-406 + UR5e Cobot
Sem histórico de dados              →      HDA via TimescaleDB
Sem semântica                       →      Semantic IDs (ECLASS, IRI)
Sem repositório aberto              →      GitHub open-aas/CPS-406 + Zenodo DOI
Validação subjetiva                 →      5 experimentos quantitativos
```

---

## PARTE 5 — Checklist para Submissão

### Antes de escrever

- [ ] Revisar literatura: buscar papers sobre AAS + OPC UA (2022–2025) no IEEE Xplore, Scopus
- [ ] Mapear gaps: confirmar que Faaster + AAS V3 para planta modular completa não existe na literatura
- [ ] Escolher o journal-alvo e ler suas Author Guidelines
- [ ] Definir quais dos 5 experimentos serão realizados

### Durante a escrita

- [ ] Abstract com problema, método, resultado e impacto em ≤ 250 palavras
- [ ] Introdução com motivação quantificada (não apenas qualitativa)
- [ ] Revisão crítica da literatura — não apenas descrever, mas comparar e identificar lacunas
- [ ] Seção de metodologia reprodutível — outro pesquisador deve conseguir replicar
- [ ] Resultados com análise estatística — não apenas valores pontuais
- [ ] Discussão com limitações reais e honestas
- [ ] Conclusão amarrando contribuições declaradas na introdução com resultados

### Antes de submeter

- [ ] Verificar formatação IEEE / template do journal
- [ ] Rodar gramática e estilo (Grammarly, LanguageTool)
- [ ] Revisar todas as citações (formato IEEE, DOIs válidos)
- [ ] Confirmar que repositório GitHub está público e funcional
- [ ] Gerar DOI no Zenodo para o dataset/código
- [ ] Verificar similaridade (iThenticate / Turnitin) — limite típico ≤ 20%

---

## PARTE 6 — Referências Fundamentais a Buscar

```bibtex
% AAS Standard
@techreport{IEC63278,
  title  = {Asset Administration Shell — Part 2: Metamodel (v3.0)},
  author = {{IEC}},
  year   = {2023},
  number = {IEC 63278-2}
}

% OPC UA Standard
@techreport{IEC62541,
  title  = {OPC Unified Architecture},
  author = {{IEC}},
  year   = {2020},
  number = {IEC 62541}
}

% Digital Twin original
@article{Grieves2014,
  author  = {Grieves, Michael},
  title   = {Digital Twin: Manufacturing Excellence through Virtual Factory Replication},
  year    = {2014}
}

% Digital Twin taxonomy
@article{Kritzinger2018,
  author  = {Kritzinger, Werner and others},
  title   = {Digital Twin in manufacturing: A categorical literature review and classification},
  journal = {IFAC-PapersOnLine},
  year    = {2018}
}

% AAS + OPC UA integration (buscar papers recentes 2022-2025)
% RAMI 4.0
% Platform Industrie 4.0 whitepapers
% IDTA Submodel Templates
```

---

*Documento gerado para apoiar a produção do artigo sobre o projeto CPS-406 (open-aas/CPS-406) com integração Faaster.*