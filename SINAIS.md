# Sinais do altímetro

Referência de cada net do esquemático: o que faz, onde liga, que tensão esperar e
o que o firmware e o layout precisam respeitar. As listas de conexão foram
extraídas da netlist exportada pelo KiCad (`kicad-cli sch export netlist`); se o
esquemático mudar, elas precisam ser revisadas.

Convenção de nomes: no esquemático as nets aparecem como rótulos (`VBAT`); no
KiCad (netlist, PCB, DRC) as de rótulo ganham o prefixo da folha (`/VBAT`). As de
símbolo de alimentação não têm prefixo (`+3V3`, `GND`).

> **Defeito crítico conhecido — ler antes de ligar a placa com ignitores.**
> `FIRE_B` está no PA9. No bootloader da ROM, o PA9 é configurado como
> USART1_TX em push-pull com pull-up (AN2606 rev. 61, tabela 19), e linha UART em
> repouso fica em nível alto: **Q2 liga e o canal principal dispara**. O
> bootloader roda quando o JP1 está fechado e também, sozinho, num chip com a
> flash vazia (verificação de flash vazia do STM32F04x) — ou seja, na primeira
> energização de toda placa nova. Enquanto não for corrigido: só gravar
> firmware com o USB, **sem bateria e sem ignitores**. Correção proposta: mover
> `FIRE_B` para PB4 (pino 27), que o bootloader não usa. Ver
> [Problemas conhecidos](#problemas-conhecidos).

## Resumo

| net | tipo | faixa típica | pino do MCU | netclass |
|---|---|---|---|---|
| `VBAT` | alimentação bruta | 4–16 V | — | PIRO 0,8 mm |
| `VSYS` | alimentação após OR | 3,7–15,7 V | — | POWER 0,4 mm |
| `VBUS` | alimentação USB | 4,4–5,25 V | — | POWER 0,4 mm |
| `+3V3` | alimentação regulada | 3,3 V | VDD, VDDA, VDDIO2 | POWER 0,4 mm |
| `GND` | referência | 0 V | VSS, VSSA | POWER 0,4 mm + planos |
| `VB_SNS` | analógico | 0,36–1,45 V | PA2 / ADC_IN2 | Default |
| `VU_SNS` | analógico/digital | 0 ou ~2,5 V | PB0 / ADC_IN8 | Default |
| `FIRE_A` | saída digital | 0 / 3,3 V | PA8 | Default |
| `FIRE_B` | saída digital | 0 / 3,3 V | PA9 ⚠ | Default |
| `GATE_A`, `GATE_B` | gate de MOSFET | 0 / 3,3 V | — | Default |
| `PYRO_A`, `PYRO_B` | potência (dreno) | 0 a VBAT | — | PIRO 0,8 mm |
| `SNS_A`, `SNS_B` | analógico | 0 a 1,45 V | PA0, PA1 | Default |
| `SCK`, `MOSI`, `MISO` | SPI1 | 0 / 3,3 V | PA5, PA7, PA6 | Default |
| `CS_BARO`, `CS_FLSH` | seleção SPI, ativo baixo | 0 / 3,3 V | PA4, PA3 | Default |
| `WPn`, `HOLDn` | controle da flash | 3,3 V fixo | — | Default |
| `USB_DP`, `USB_DM` | USB FS | 0–3,3 V | PA12, PA11 | Default |
| `DP_CON`, `DM_CON` | USB FS, lado do conector | 0–3,3 V | — | Default |
| `SWDIO`, `SWCLK` | depuração | 0 / 3,3 V | PA13, PA14 | Default |
| `NRST` | reset, ativo baixo | 0 / 3,3 V | NRST | Default |
| `BOOT0` | modo de boot | 0 / 3,3 V | PB8/BOOT0 | Default |
| `BEEP` | saída PWM | 0 / 3,3 V, 4 kHz | PB1 / TIM3_CH4 | Default |
| `GATE_BZ` | gate de MOSFET | 0 / 3,3 V | — | Default |
| `BUZZ` | dreno do buzzer | 0 a ~3,7 V | — | Default |
| `STAT` | LED, ativo baixo | 0 / 3,3 V | PA15 | Default |
| `LED_A` | anodo do LED | 2–3,3 V | — | Default |

---

## Alimentação

### `VBAT` — bateria

Tensão crua da bateria, direto do borne. Alimenta a lógica (via D1) e é a fonte
da corrente de disparo dos dois canais pirotécnicos.

- **Conexões:** J1.1 (+ da bateria), C1.1 (100 µF), D1.2 (anodo), R1.1 (divisor
  de medição), J4.1 e J5.1 (um lado de cada ignitor).
- **Faixa:** 4–16 V. O teto é a entrada máxima do regulador U1 e do C2 (25 V)
  com margem; o piso é 3,3 V + queda do regulador (~0,1 V a 25 mA) + queda do D1
  (~0,3 V). Uso típico: LiPo 2S (6,0–8,4 V) ou 9 V.
- **Corrente:** ~25 mA contínuos para a lógica; alguns ampères por até ~1 s
  durante um disparo, através do ignitor.
- **Layout:** netclass PIRO (0,8 mm, folga 0,3 mm). C1 fica junto a J1 para
  sustentar o pico de disparo.
- **Cuidados:** não há proteção contra inversão de polaridade nem contra
  sobretensão nesta net (ver [Problemas conhecidos](#problemas-conhecidos)). Não
  há chave na placa: bateria ligada = placa ligada; prever chave externa em série.

### `VSYS` — alimentação do regulador

Saída do "OU" de diodos entre bateria e USB; existe só para alimentar o U1.

- **Conexões:** D1.1 e D2.1 (catodos), C2.1 (10 µF/25 V), U1.2 (VI).
- **Faixa:** a maior entre VBAT − 0,3 V e VBUS − 0,3 V. Só com USB: ~4,7 V. Com
  bateria de 7,4 V: ~7,1 V.
- **Papel de segurança:** os bornes pirotécnicos ficam *antes* do D1, em `VBAT`.
  Com só o USB, `VSYS` existe e o MCU funciona, mas `VBAT` fica sem tensão e
  nenhum canal pode disparar.
- **Cuidados:** C2 (10 µF) dá pouca autonomia (~2,5 V/ms a 25 mA) se `VBAT`
  despencar num disparo. Com LiPo isso não ocorre; com 9 V de alta resistência
  interna pode resetar o MCU.

### `VBUS` — 5 V do USB

- **Conexões:** J3.1 (VBUS do conector), D2.2 (anodo), U5.5 (referência do
  protetor ESD), C14.1 (1 µF), C15.1 (100 nF), R6.1 (detecção de USB).
- **Faixa:** 4,4–5,25 V com host conectado; 0 V sem cabo (C14/C15 descarregam
  pelo divisor R6/R7).
- **Cuidados:** sem fusível. D2 impede que a bateria alimente o host.

### `+3V3` — alimentação regulada

Saída do MCP1703 (U1). Alimenta toda a lógica.

- **Conexões:** U1.3 (VO); U2.1 (VDD), U2.5 (VDDA), U2.17 (VDDIO2); U3.1 (VDD
  do barômetro); U4.8 (VCC da flash); LS1.1 (+ do buzzer); D3.1 (catodo do
  diodo de roda livre); R18.1 (LED); R4.1, R5.1 (pull-ups da flash); J2.1 (SWD);
  JP1.1 (BOOT0). Desacoplamento: C3 (10 µF), C4 (100 nF) no regulador; C6, C7
  (100 nF) e C8 (1 µF) no MCU; C9 (100 nF) e C10 (1 µF) no VDDA; C12 no
  barômetro; C13 na flash.
- **Capacidade:** 250 mA (MCP1703). Consumo: MCU ~20 mA a 48 MHz; flash até
  ~25 mA ao gravar; barômetro ~1,4 mA durante a conversão; buzzer ~100 mA de
  pico a 4 kHz; LED ~1 mA.
- **Firmware:** VDDA está ligado ao `+3V3`, então é também a referência do ADC.
  A tolerância do regulador (±2 % no pior caso) entra direto nas medidas de
  tensão. Para precisão, medir o VREFINT e usar o valor de calibração de fábrica
  (`VREFINT_CAL`) para corrigir.
- **Cuidados:** o buzzer puxa pico de ~100 mA deste trilho. Não tocar o buzzer
  durante medidas de pressão que definem a referência de solo.

### `GND`

- **Conexões:** todos os retornos — J1.2 (− da bateria), fonte de Q1/Q2/Q3, U1.1,
  U2.16 (VSS) e U2.32 (VSSA), U3.3 e **U3.2 (PS)**, U4.4, U5.2, J3.5 e
  J3.SH (blindagem do USB), J2.5, e o lado frio dos capacitores e divisores.
- **U3.2 em GND é intencional:** o pino PS do MS5607 em nível baixo seleciona o
  modo SPI.
- **Layout:** plano nas duas camadas, costurado por vias. Pads SMD ligam ao plano
  sem alívio térmico; os passantes (bornes) têm alívio. O retorno da corrente de
  disparo vai da fonte de Q1/Q2 até J1.2 pelo plano superior.

---

## Medição

### `VB_SNS` — tensão da bateria

`VBAT` dividido por 11 (R1 = 100 k, R2 = 10 k), filtrado por C5 (100 nF).

- **Conexões:** R1.2, R2.1, C5.1, U2.8 (PA2 / ADC_IN2).
- **Valores:** 4 V → 0,364 V; 7,4 V → 0,673 V; 8,4 V → 0,764 V; 9 V → 0,818 V;
  16 V → 1,455 V.
- **Firmware:** `VBAT = leitura × 3,3 / 4095 × 11` (resolução ~8,9 mV por
  contagem). Impedância de fonte de 9,1 kΩ, mas o C5 segura a amostra; qualquer
  tempo de amostragem funciona. Medida tomada antes do D1, ou seja, é a tensão
  real da bateria.
- **Consumo:** o divisor drena VBAT/110 kΩ o tempo todo (67 µA a 7,4 V).

### `VU_SNS` — detecção de USB

`VBUS` dividido por 2 (R6 = R7 = 100 k).

- **Conexões:** R6.2, R7.1, U2.14 (PB0 / ADC_IN8).
- **Valores:** ~2,5 V com cabo conectado; 0 V sem cabo.
- **Firmware:** permite decidir entre modo de bancada (USB: download de dados) e
  modo de voo. Ler pelo ADC com limiar de ~1,5 V é mais robusto que a leitura
  digital.

---

## Canais pirotécnicos

Os dois canais são idênticos; A é o apogeu (drogue) e B o principal. Os nomes
abaixo valem para A; para B troque Q1→Q2, J4→J5, R8–R11→R12–R15, C16→C17,
PA8→PA9, PA0→PA1.

```
VBAT ── J4.1 ──[ ignitor ]── J4.2 = PYRO_A ──┬── Q1 dreno      Q1 fonte ── GND
                                             └── R10 100k ──┬── SNS_A ── PA0
FIRE_A (PA8) ── R8 100R ── GATE_A ── Q1 gate                ├── R11 10k ── GND
                              └── R9 100k ── GND            └── C16 10n ── GND
```

### `FIRE_A` / `FIRE_B` — comando de disparo

- **Conexões:** A: U2.18 (PA8) → R8.1. B: U2.19 (PA9) → R12.1.
- **Lógica:** ativo alto. Nível alto liga o MOSFET e passa corrente pelo
  ignitor.
- **Firmware:** configurar como saída push-pull em nível baixo antes de qualquer
  outra inicialização. Manter o pulso pelo tempo necessário ao ignitor (tipicamente
  0,5–1 s) e desligar. Não habilitar o MCO no PA8.
- **Segurança:** com o MCU em reset ou sem firmware, os pinos ficam em alta
  impedância e R9/R13 mantêm o MOSFET desligado. **Exceção: o bootloader da ROM
  aciona o PA9** — ver o aviso no topo deste documento.

### `GATE_A` / `GATE_B` — gate do MOSFET

- **Conexões:** A: R8.2, R9.1, Q1.1 (G). B: R12.2, R13.1, Q2.1 (G).
- **Valores:** 0 V desligado; ~3,3 V ligado. O AO3400A conduz plenamente com
  3,3 V no gate (R_DS(on) de dezenas de mΩ).
- **Função dos resistores:** R8/R12 (100 Ω) limitam o pico de corrente de carga
  do gate; R9/R13 (100 kΩ) garantem gate em GND quando o pino do MCU flutua.

### `PYRO_A` / `PYRO_B` — dreno / lado frio do ignitor

- **Conexões:** A: J4.2, Q1.3 (D), R10.1. B: J5.2, Q2.3 (D), R14.1.
- **Valores:** ≈ VBAT com ignitor intacto e canal desligado; ~0 V com o canal
  ligado; ~0 V sem ignitor (puxado pelo divisor R10+R11).
- **Corrente:** a corrente de disparo inteira passa por aqui. Netclass PIRO
  (0,8 mm, folga 0,3 mm). Tensão máxima do MOSFET: 30 V.

### `SNS_A` / `SNS_B` — teste de continuidade

`PYRO_x` dividido por 11 (100 k / 10 k), filtrado por C16/C17 (10 nF, τ ≈ 91 µs).

- **Conexões:** A: R10.2, R11.1, C16.1, U2.6 (PA0 / ADC_IN0). B: R14.2, R15.1,
  C17.1, U2.7 (PA1 / ADC_IN1).
- **Interpretação:** o divisor é igual ao de `VB_SNS`, então a comparação é
  direta:
  - `SNS_x ≈ VB_SNS` → ignitor presente (continuidade);
  - `SNS_x ≈ 0` → ignitor ausente ou já queimado;
  - limiar sugerido: `SNS_x > 0,5 × VB_SNS`.
- **Segurança:** a corrente de teste pelo ignitor é VBAT/110 kΩ — no máximo
  145 µA a 16 V, três ordens de grandeza abaixo da corrente de não-disparo
  típica de um e-match (~250 mA).
- **Limitação:** um ignitor em curto lê igual a um ignitor bom.
- **Uso após o disparo:** `SNS_x` cair para 0 depois do pulso confirma que o
  ignitor abriu (queimou).

---

## Barramento SPI (barômetro e flash)

SPI1 do STM32 (função alternativa AF0) compartilhado entre U3 (MS5607) e U4
(W25Q16JV).

| net | MCU | U3 (MS5607) | U4 (W25Q16JV) |
|---|---|---|---|
| `SCK` | U2.11 (PA5) | U3.8 (SCLK) | U4.6 (CLK) |
| `MOSI` | U2.13 (PA7) | U3.7 (SDI/SDA) | U4.5 (DI/IO0) |
| `MISO` | U2.12 (PA6) | U3.6 (SDO) | U4.2 (DO/IO1) |
| `CS_BARO` | U2.10 (PA4) | U3.4 e U3.5 (CSB) | — |
| `CS_FLSH` | U2.9 (PA3) | — | U4.1 (/CS) |

- **Modo SPI:** 0 (CPOL = 0, CPHA = 0); os dois chips também aceitam o modo 3.
- **Clock:** até 20 MHz pelo MS5607. Sugestão: 12 MHz (48 MHz / 4).
- **`CS_BARO` / `CS_FLSH`:** ativos em nível baixo. O firmware deve configurá-los
  como saída em nível alto antes de habilitar o SPI. Nunca baixar os dois ao
  mesmo tempo. U3.5 é uma conexão interna do MS5607, ligada ao CSB.
- **`MISO`:** os dois escravos deixam a saída em alta impedância com o CS alto;
  só fala quem está selecionado.
- **Concorrência:** as conversões do MS5607 são disparadas por comando e lidas
  depois; a gravação da flash entra nos intervalos. Não há acesso simultâneo.

### `WPn` / `HOLDn` — controle da flash

- **Conexões:** `WPn`: U4.3 (/WP/IO2) ↔ R4.2 (10 k para `+3V3`).
  `HOLDn`: U4.7 (/HOLD/RESET/IO3) ↔ R5.2 (10 k para `+3V3`).
- **Valor:** 3,3 V fixo (inativos). Mantêm a flash sem proteção de escrita por
  hardware e sem pausa.
- **Nota:** esses pinos não chegam ao MCU (e o STM32F042 não tem QSPI), então o
  modo quad **não** é possível nesta placa; a flash opera em SPI simples.

---

## USB

```
J3 (D+) ── DP_CON ── U5 pino 1 ═══ U5 pino 6 ── USB_DP ── PA12
J3 (D−) ── DM_CON ── U5 pino 3 ═══ U5 pino 4 ── USB_DM ── PA11
```

O USBLC6-2SC6 é de passagem: os pinos 1/6 e 3/4 são a mesma linha por dentro,
com diodos de grampeamento para GND e para `VBUS`. Há dois nomes por linha
apenas porque o layout obriga o sinal a passar pelo protetor antes de ir ao MCU.

### `DP_CON` / `DM_CON` — lado do conector

- **Conexões:** `DP_CON`: J3.3 (D+), U5.1. `DM_CON`: J3.2 (D−), U5.3.

### `USB_DP` / `USB_DM` — lado do MCU

- **Conexões:** `USB_DP`: U5.6, U2.22 (PA12). `USB_DM`: U5.4, U2.21 (PA11).
- **Firmware:** USB Full Speed (12 Mbit/s) sem cristal: HSI48 com o CRS
  sincronizado ao SOF do host. O pull-up de 1,5 kΩ no D+ é interno ao STM32
  (bit DPPU); não há resistor externo.
- **Layout:** trilhas curtas e paralelas. Em 12 Mbit/s com estas distâncias, a
  impedância diferencial não é crítica.
- **J3.4 (ID):** sem conexão; não é usado (sem OTG).

---

## Depuração e boot

### `SWDIO` / `SWCLK`

- **Conexões:** `SWDIO`: U2.23 (PA13), J2.2. `SWCLK`: U2.24 (PA14), J2.3.
- **Firmware:** são SWD por padrão após o reset (SWDIO com pull-up interno,
  SWCLK com pull-down interno). Não reconfigurar esses pinos no firmware, ou a
  depuração só volta via BOOT0 ou reset sob o depurador.

### `NRST` — reset

- **Conexões:** U2.4 (NRST), C11.1 (100 nF), J2.4.
- **Lógica:** ativo baixo; pull-up interno de ~40 kΩ. C11 filtra ruído. Não há
  botão de reset; o depurador usa J2.4.

### `BOOT0` — modo de boot

- **Conexões:** U2.31 (PB8/BOOT0), R3.1 (10 k para GND), JP1.2.
- **Lógica:** JP1 aberto → R3 mantém BOOT0 em 0 → executa o firmware da flash.
  JP1 fechado → BOOT0 em 3,3 V → bootloader da ROM (DFU pelo USB, USART1, USART2
  ou I2C1).
- **Atenção:** o STM32F04x também entra no bootloader sozinho quando a flash
  está vazia, mesmo com BOOT0 em 0. **No bootloader o PA9 (`FIRE_B`) vai a nível
  alto** — ver [Problemas conhecidos](#problemas-conhecidos).

### Conector J2 (SWD, passo 1,27 mm)

| pino | net |
|---|---|
| 1 | `+3V3` |
| 2 | `SWDIO` |
| 3 | `SWCLK` |
| 4 | `NRST` |
| 5 | `GND` |

---

## Indicação

### `BEEP` — comando do buzzer

- **Conexões:** U2.15 (PB1 / TIM3_CH4), R16.1.
- **Firmware:** PWM de 4 kHz, ciclo de 50 % (frequência nominal do CMT-8504).
  Nível baixo = silêncio.

### `GATE_BZ`

- **Conexões:** R16.2 (100 Ω), R17.1 (100 k para GND), Q3.1 (G).
- **Função:** igual à dos canais pirotécnicos — R17 mantém o buzzer mudo com o
  MCU em reset.

### `BUZZ` — dreno do buzzer

- **Conexões:** LS1.2 (−), Q3.3 (D), D3.2 (anodo).
- **Valores:** ~3,3 V com Q3 desligado (o buzzer liga o dreno ao `+3V3` pela
  bobina); ~0 V com Q3 ligado. No desligamento a bobina gera um pico que o D3
  grampeia em ~3,7 V.

### `STAT` — LED de estado

- **Conexões:** U2.25 (PA15), D4.1 (catodo).
- **Lógica:** ativo **baixo** — PA15 em 0 acende o LED.
- **Corrente:** (3,3 V − V_F) / 1 kΩ, ~1 mA para um LED verde.

### `LED_A`

- **Conexões:** R18.2 (1 k para `+3V3`), D4.2 (anodo). Nó interno, sem função
  para o firmware.

---

## Pinos sem conexão

| pino | função | motivo |
|---|---|---|
| U2.2 PF0, U2.3 PF1 | OSC_IN/OSC_OUT | USB sem cristal |
| U2.20 PA10 | USART1_RX | livre |
| U2.26–30 PB3–PB7 | GPIO | livres (PB6/PB7 = I2C1, útil para expansão) |
| J3.4 | ID do USB | sem OTG |

**Firmware:** configurar os pinos livres como analógicos (menor consumo e sem
entrada flutuando).

---

## Valores esperados na bancada

Com bateria de 7,4 V, USB desconectado, ignitores de ~1,5 Ω nos dois canais,
firmware parado:

| ponto | esperado |
|---|---|
| `VBAT` | 7,4 V |
| `VSYS` | ~7,1 V |
| `+3V3` | 3,30 V (±2 %) |
| `VB_SNS` | ~0,67 V |
| `SNS_A`, `SNS_B` | ~0,67 V (sem ignitor: ~0 V) |
| `VU_SNS` | 0 V (com USB: ~2,5 V) |
| `PYRO_A`, `PYRO_B` | ~7,4 V |
| `GATE_A`, `GATE_B`, `GATE_BZ` | 0 V |
| `BUZZ` | ~3,3 V |
| `BOOT0` | 0 V (JP1 aberto) |
| `NRST` | ~3,3 V |

---

## Problemas conhecidos

1. **Crítico — `FIRE_B` no PA9 dispara no bootloader.** Descrito no topo.
   Correção: mover `FIRE_B` para PB4 (pino 27). Pelo AN2606, o bootloader do F04x
   não usa o PB4, e na saída do reset ele fica em entrada flutuante, com R13
   segurando o gate. Evitar também o PA10 (USART1_RX com pull-up de ~40 kΩ no
   bootloader, que contra os 100 kΩ do R13 poria ~2,4 V no gate) e o PA14/PA15
   (USART2 do bootloader). O `FIRE_A` no PA8 está correto: o bootloader não usa
   esse pino.
2. **Alto — bateria invertida dispara os ignitores.** Com `VBAT` negativo, a
   corrente passa GND → diodo de corpo de Q1/Q2 → ignitor → bateria, limitada só
   pela resistência do ignitor. Correção: MOSFET canal P em série na entrada de
   bateria, ou conector polarizado.
3. **Médio — Q3 (BSS138) no limite de corrente.** O buzzer pede ~100 mA de pico
   e o BSS138 é especificado para ~200 mA contínuos, com resistência de alguns
   ohms a 3,3 V no gate (o buzzer perde volume e o MOSFET esquenta). Trocar por
   AO3400A, o mesmo de Q1/Q2, resolve e unifica a BOM.
4. **Baixo — `CS_BARO` e `CS_FLSH` flutuam durante o reset.** Até o firmware
   configurá-los, os chips podem ver seleção espúria (inofensivo enquanto o SCK
   estiver parado). Pull-ups de 100 kΩ para `+3V3` nas duas linhas deixam o
   estado definido.
5. **Baixo — sem proteção de sobretensão em `VBAT`.** Acima de 16 V o regulador
   é o primeiro a falhar. Um TVS de 18 V na entrada protege contra picos.
