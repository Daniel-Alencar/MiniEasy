# Altímetro de dois eventos — classe EasyMini

Esquemático KiCad 10 de um altímetro barométrico de recuperação dupla (apogeu +
principal), equivalente em função ao Altus Metrum EasyMini: sensor barométrico,
registro de voo em flash, dois canais pirotécnicos com teste de continuidade,
download por USB. Sem GPS, sem acelerômetro, sem telemetria.

Arquivos:

| arquivo | conteúdo |
|---|---|
| `altimetro.kicad_sch` | esquemático, folha única A2, formato nativo KiCad 10 |
| `altimetro.kicad_pro` | projeto (inclui netclass `PIRO` de 1,0 mm) |
| `altimetro.pdf` | plotagem do esquemático |
| `bom.csv` | lista de materiais exportada pelo KiCad, 54 componentes |
| `gerador/` | scripts que geram e verificam o esquemático |

## Arquitetura

```
J1 ──┬── C1 100µF ──────────────────► VBAT ──┬── J4 pino 1 (piro apogeu)
BAT  │   (reservatório de disparo)           └── J5 pino 1 (piro principal)
4-16V└── D1 ─┐
             ├─ VSYS ── U1 MCP1703 ── +3V3 ── MCU, baro, flash, buzzer
J3 USB ── D2 ┘         (SOT-89)
   └── U5 USBLC6 ── D+/D- ── U2 STM32F042K6T6 ──┬── SPI1 ──┬── U3 MS5607 (baro)
                                                │          └── U4 W25Q16 (flash)
                                                ├── ADC ───── continuidade A/B + VBAT
                                                ├── GPIO ──── Q1/Q2 AO3400A (disparo)
                                                └── TIM3 ──── Q3 + LS1 (buzzer)
```

Sete blocos no esquemático, numerados na folha: alimentação, MCU, barômetro +
memória, USB, canal A, canal B, aviso sonoro.

## Mapa de pinos do STM32F042K6T6 (LQFP32)

| pino | função | net | uso |
|---|---|---|---|
| 1, 5, 17 | VDD, VDDA, VDDIO2 | `+3V3` | C6/C9/C7 = 100 n, C8/C10 = 1 µF |
| 16, 32 | VSS, VSSA | `GND` | |
| 4 | NRST | `NRST` | C11 100 n + J2 pino 4 |
| 6 | PA0 / ADC_IN0 | `SNS_A` | continuidade canal apogeu |
| 7 | PA1 / ADC_IN1 | `SNS_B` | continuidade canal principal |
| 8 | PA2 / ADC_IN2 | `VB_SNS` | tensão de bateria (÷11) |
| 9 | PA3 | `CS_FLSH` | chip select da flash |
| 10 | PA4 | `CS_BARO` | chip select do barômetro |
| 11, 12, 13 | PA5/6/7 = SPI1 SCK/MISO/MOSI | `SCK` `MISO` `MOSI` | AF0 |
| 14 | PB0 / ADC_IN8 | `VU_SNS` | detecção de VBUS (÷2) |
| 15 | PB1 / TIM3_CH4 | `BEEP` | geração de tom |
| 18 | PA8 | `FIRE_A` | disparo apogeu |
| 19 | PA9 | `FIRE_B` | disparo principal |
| 21, 22 | PA11, PA12 | `USB_DM` `USB_DP` | USB FS device |
| 23, 24 | PA13, PA14 | `SWDIO` `SWCLK` | depuração |
| 25 | PA15 | `STAT` | LED de estado (dreno) |
| 31 | PB8 / BOOT0 | `BOOT0` | R3 10 k para GND + JP1 |
| 2, 3, 20, 26–30 | PF0, PF1, PA10, PB3–PB7 | — | marcados *no connect* |

Pinagens conferidas contra o datasheet: pino 17 é VDDIO2 e pino 16 é VSS (ST
STM32F042x4/x6); MS5607-02BA03 pino 4 = CSB e pino 5 = conexão interna, ambos no
mesmo net (datasheet TE, seção *Pin Configuration*). Atenção ao MCP1703: a
numeração muda com o encapsulamento — em SOT-89 é 1 = GND, 2 = VIN, 3 = VOUT
(em SOT-223 o pino 1 é VIN).

## Decisões de projeto

**STM32F042K6T6.** Mesma escolha do EasyMini v3. O que importa aqui é o USB
*crystal-less*: o periférico USB roda do HSI48 corrigido pelo CRS, sincronizado
ao SOF do host. Isso elimina cristal, dois capacitores e a área deles; PF0/PF1
ficam livres. Em troca, não há base de tempo precisa — o registro de voo usa o
HSI de ±1 % como base, suficiente para taxa de amostragem mas não para
medição de tempo absoluto.

**MS5607-02BA03 em SPI.** PS em GND seleciona SPI, compartilhando o barramento
com a flash. Resolução de 20 cm e conversão de 1 ms; limite de 1200 mbar e
10 mbar cobre do nível do mar a ~30 km. Barramento compartilhado é seguro porque
as duas conversões nunca são concorrentes: o firmware lê o barômetro e só depois
grava a amostra.

**W25Q16JV (16 Mbit).** 2 MByte dão ~24 h de voo a 100 Hz com amostra de 8
bytes — na prática, dezenas de voos sem apagar. `WPn` e `HOLDn` sobem por R4/R5
de 10 k em vez de ir direto a 3V3, para que um firmware futuro possa usar modo
quad sem alterar a placa.

**LDO MCP1703 em SOT-89, não SOT-23.** Com 16 V na entrada e 25 mA de consumo o
regulador dissipa (16 − 3,3) × 0,025 = 0,32 W. Em SOT-23 (θ_JA ≈ 250 °C/W) isso
são 80 °C de elevação; em SOT-89 (θ_JA ≈ 140 °C/W), 45 °C. O Iq de 2 µA importa
porque a placa fica armada na bancada por horas.

**OR de fontes por Schottky (D1/D2).** Bateria e USB alimentam o 3V3 por diodos
separados. O efeito colateral é a propriedade de segurança mais importante da
placa: `VBAT` alimenta os bornes pirotécnicos *diretamente*, não passa pelos
diodos — com só o USB conectado os canais ficam sem energia. Dá para programar e
baixar dados com os ignitores ligados.

**Disparo em lado baixo com pulldown no gate.** Q1/Q2 (AO3400A, 30 V, 5,7 A,
R_DS ≈ 30 mΩ) chaveiam o lado de GND do ignitor. R9/R13 de 100 k mantêm o gate
em GND enquanto o MCU está em reset, sem firmware ou travado — um pino em
tri-state não dispara nada. R8/R12 de 100 Ω limitam o pico de corrente de gate.

**Continuidade por divisor no dreno.** R10/R11 (100 k/10 k) medem o dreno de Q1.
Com ignitor intacto o nó fica em VBAT/11 (1,45 V em 16 V, 0,36 V em 4 V); com
ignitor aberto o divisor puxa o nó para 0 V. A corrente de teste que passa pelo
ignitor é VBAT/110 k, no máximo 145 µA — três ordens de grandeza abaixo da
corrente de não-disparo típica (250 mA) de um e-match. C16/C17 de 10 n filtram o
nó do ADC.

**C1 de 100 µF.** O disparo é um curto de ~1 Ω por ~1 s; sem reservatório local
a queda em VBAT faz o MCU resetar no pior momento possível. C1 fica no borne de
bateria, no mesmo laço de corrente dos bornes pirotécnicos.

**JP1 (BOOT0).** No STM32F042, BOOT0 é multiplexado com PB8. Fechando JP1 a
placa entra no bootloader DFU da ROM e aceita firmware pelo próprio USB, sem
programador. J2 (SWD 1×5, passo 1,27 mm) fica para depuração.

## Observações sobre o desenho

As ligações são feitas por **rótulos em stubs de 2,54 mm**: cada pino tem um fio
curto com o nome do net, em vez de fios longos atravessando a folha. É legal e
sem ambiguidade — a netlist extraída da geometria é idêntica à tabela de nets do
gerador — mas é um estilo compacto, não o traçado "bonito" de um esquemático
feito à mão. Reposicionar e traçar fios de verdade nos blocos é trabalho de
edição normal no Eeschema e não altera a netlist.

D1/D2/D3 estão desenhados com o catodo à esquerda (orientação padrão do símbolo,
sem espelhamento). Os rótulos deixam o sentido claro: em D1, `VBAT` entra pelo
anodo à direita e `VSYS` sai pelo catodo à esquerda.

## Notas para o layout da PCB

1. O laço de disparo (J1 → C1 → J4/J5 → Q1/Q2 → GND) carrega alguns ampères por
   ~1 s. Netclass `PIRO` já está configurada em 1,0 mm; mantenha o laço curto e
   com área pequena, e não passe sinais de ADC por dentro dele.
2. O MS5607 precisa de abertura de ventilação para a pressão ambiente e **não
   pode ser lavado** (o datasheet é explícito: usar pasta no-clean). Mantenha a
   área reservada sob o sensor livre de trilhas, conforme o pad layout da TE.
3. Separe o GND de retorno pirotécnico do GND analógico do divisor de
   continuidade, unindo-os num único ponto junto ao borne de bateria.
4. U5 (USBLC6) vai o mais próximo possível do conector USB, antes de qualquer
   outra coisa nas linhas D+/D-.
5. Reserve lugar para fixar a bateria e os fios dos ignitores: são eles que
   sofrem a aceleração, não os componentes SMD.

## Verificação

`gerador/verificar.sh` gera o esquemático a partir das bibliotecas do KiCad
instalado e só grava o resultado se tudo passar:

1. o gerador recusa pino sem net e sem *no connect*, pino em dois nets, e dois
   símbolos de alimentação no mesmo ponto;
2. `check_sch.py` reextrai a netlist da geometria do arquivo e compara com a
   tabela `NETS`;
3. `check_layout.py` procura sobreposição de símbolos e rótulos e itens fora da
   folha;
4. `kicad-cli sch upgrade` converte para o formato nativo;
5. ERC do KiCad com todas as severidades — **0 erros, 0 avisos**;
6. `netcheck.py` compara a netlist exportada pelo próprio KiCad com a tabela
   `NETS` e confere cada footprint contra o filtro de footprint do símbolo;
7. exporta `altimetro.pdf` e `bom.csv`.

## O que não está feito

- PCB, firmware e certificação.
- Proteção contra inversão de polaridade da bateria: D1 protege só o ramo de
  3V3. Os bornes pirotécnicos estão em `VBAT` direto, então bateria invertida
  polariza Q1/Q2 pelo diodo de corpo. Se isso preocupar, um P-FET em série na
  entrada resolve, ao custo de R_DS no caminho de disparo.
- Um elemento de armamento em série (chave física ou segundo FET) nos canais
  pirotécnicos. O EasyMini também não tem, mas é o acréscimo que eu faria antes
  de tratar a placa como produto.

## Regenerar

```sh
gerador/verificar.sh                      # usa /usr/share/kicad/symbols
gerador/verificar.sh /caminho/symbols     # outra instalação
```

A tabela `NETS` em `gerador/gen_sch.py` é a fonte da verdade das ligações: o
gerador falha se algum pino ficar sem net e sem *no connect*, se um pino aparecer
em dois nets, ou se dois símbolos de alimentação caírem no mesmo ponto. Depois de
editar o esquemático à mão no Eeschema, não regenere — o gerador sobrescreve o
posicionamento.
