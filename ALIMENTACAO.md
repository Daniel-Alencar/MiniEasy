# O sistema de alimentação, explicado

Por que o bloco de alimentação deste altímetro é do jeito que é: o "OU" de
diodos, a escolha do regulador, o reservatório de disparo e os sete capacitores
de desacoplamento espalhados pela placa.

Referência seca de cada sinal (pinos, tensões, notas de firmware) em
[SINAIS.md](SINAIS.md). Aqui o assunto é o *porquê*.

## Visão geral

```
            ┌──────────────── VBAT ─────────────────┬──► J4.1 (ignitor do apogeu)
J1 (+) ─────┤                                       └──► J5.1 (ignitor principal)
bateria     ├── C1 100 µF (reservatório de disparo)
4–16 V      ├── R1/R2 ÷11 ──► PA2 (mede a bateria)
            └── D1 ──┐
                     ├── VSYS ── C2 ── U1 MCP1703 ── +3V3 ──► MCU, barômetro,
J3 USB (5 V) ── D2 ──┘                                        flash, buzzer, LED
```

Há quatro tensões porque há duas fontes e duas cargas com exigências opostas:

| net | o que é | quem alimenta |
|---|---|---|
| `VBAT` | bateria crua, 4–16 V | os ignitores, direto |
| `VBUS` | 5 V do USB | o protetor de ESD e o D2 |
| `VSYS` | o que sai do "OU" de diodos | só o regulador |
| `+3V3` | saída regulada | toda a lógica |

A lógica puxa ~25 mA constantes e exige tensão estável. Os ignitores puxam
alguns ampères por cerca de um segundo e não ligam para a qualidade da tensão.
Misturar os dois no mesmo trilho é o erro que este bloco inteiro evita.

---

## O "OU" de diodos

"OU" aqui é o OU lógico: o VSYS recebe energia da bateria **ou** do USB.

Um diodo só conduz quando o anodo está mais positivo que o catodo, com uma
folga de ~0,3 V num Schottky. Como os dois catodos (D1 e D2) estão no mesmo
ponto, a fonte de tensão mais alta vence sozinha, sem nenhuma lógica de
controle:

| situação | quem conduz | VSYS |
|---|---|---|
| só USB (5 V) | D2 | ~4,7 V |
| só bateria (7,4 V) | D1 | ~7,1 V |
| as duas | só D1 — o VSYS em 7,1 V bloqueia o D2 | ~7,1 V |
| nenhuma | — | 0 V |

**Por que não ligar as duas fontes direto uma na outra.** Elas brigariam. A
bateria de 7,4 V empurraria corrente para dentro da porta USB do computador, que
espera receber 5 V, e o USB tentaria carregar a bateria sem nenhum controle de
carga. Os diodos permitem corrente só no sentido fonte → VSYS.

**O custo** é a queda de ~0,3 V no diodo. A 25 mA isso são 7,5 mW, irrelevante
em calor, mas tira 0,3 V do fundo da faixa útil da bateria: a regulação começa a
falhar por volta de 3,7 V em vez de 3,4 V. A especificação de 4 V no borne tem
margem sobre isso.

**O efeito colateral que vale mais que o resto.** Os bornes dos ignitores ligam
em `VBAT`, *antes* do D1. Com só o cabo USB conectado, o MCU liga e funciona,
mas o `VBAT` fica em 0 V e nenhum canal tem como disparar. Dá para gravar
firmware e baixar dados de voo na bancada com os ignitores conectados. Essa
propriedade é consequência direta de onde o diodo foi posto.

---

## O regulador U1 (MCP1703, 3,3 V)

Três motivos para este componente, nesta embalagem:

**Entrada até 16 V.** A maioria dos reguladores pequenos aceita 6 V. Este
precisa engolir uma LiPo 2S carregada, ou 9 V, com folga.

**Consumo próprio de 2 µA.** A placa fica armada na rampa por horas antes do
lançamento. Um regulador com consumo de 50 µA seria um dreno permanente
comparável ao resto do circuito em repouso.

**Encapsulamento SOT-89, não SOT-23.** Um LDO queima a diferença de tensão em
calor. No pior caso:

```
(16 V − 3,3 V) × 25 mA = 0,32 W
```

Com a resistência térmica aproximada de cada encapsulamento (~250 °C/W no
SOT-23, ~140 °C/W no SOT-89 — valores de ordem de grandeza, dependem da área de
cobre), isso dá cerca de 80 °C de elevação no SOT-23 contra ~45 °C no SOT-89. O
encapsulamento maior custa alguns milímetros quadrados e resolve.

**Atenção à pinagem:** no SOT-89 é 1 = GND, 2 = entrada, 3 = saída. No SOT-223
do mesmo chip o pino 1 é a entrada. Foi exatamente esse o erro que o ERC pegou
na primeira versão do esquemático — a bateria entrava no pino de terra.

---

## C1: o reservatório de disparo

Disparar um e-match é praticamente curto-circuitar a bateria: a resistência é de
1 a 2 Ω e a corrente, de alguns ampères, dura cerca de um segundo.

Toda bateria tem resistência interna. Durante esse pulso, a tensão nos terminais
cai. Se cair o bastante, o VSYS acompanha, o regulador sai de regulação e **o
MCU reseta no meio da sequência de recuperação** — o pior momento possível.

C1 (100 µF, junto ao borne da bateria) é um reservatório local que fornece o
pico e se recarrega depois. O D1 ajuda pelo mesmo motivo pelo qual existe: se o
`VBAT` afundar abaixo do `VSYS`, ele bloqueia e impede que o C2 se descarregue
de volta para dentro do laço de disparo.

**Limitação conhecida:** o C2 (10 µF) sustenta o VSYS por pouco tempo, ~2,5 V/ms
a 25 mA. Com LiPo isso não é problema. Com bateria de 9 V, que tem resistência
interna alta, o conjunto pode não segurar — vale aumentar o C2 ou confiar no
detector de subtensão do MCU.

---

## Desacoplamento: por que sete capacitores e não um

Esta é a parte que o esquemático esconde, e a pergunta razoável é: se `+3V3` é
uma net só, por que não um capacitor grande no regulador?

### O que acontece quando um CI comuta

Um circuito digital não consome corrente de forma constante. A cada borda de
clock (48 MHz no MCU), milhares de transistores comutam juntos e puxam picos que
duram nanossegundos. Quem fornece esse pico?

O regulador não: ele reage em microssegundos, mil vezes mais devagar. Quem
fornece é o capacitor mais próximo.

### "Mesma net" é uma ficção do esquemático

No desenho, `+3V3` é um nó: fio ideal, impedância zero, tudo ligado a tudo
instantaneamente. Na placa, `+3V3` é cobre — e cobre tem indutância, cerca de
1 nH por milímetro nesta geometria (regra de bolso; varia com a largura da
trilha e a distância até o plano).

Distâncias reais nesta placa, medidas do arquivo da PCB:

| do regulador (U1.3) até | distância |
|---|---|
| VDD do MCU | 12,9 mm |
| VCC da flash | 36,1 mm |
| VDD do barômetro | **40,1 mm** |

Um capacitor único no regulador estaria a 40 mm do barômetro: **~40 nH de cobre
no meio do caminho**. O C12, a 1,75 mm do pino, tem ~2,5 nH contando pads e
vias.

A conta que decide é a de uma indutância diante de uma variação rápida de
corrente, V = L × di/dt. Para um pico de 50 mA em 2 ns:

| caminho | indutância | queda de tensão |
|---|---|---|
| capacitor único no regulador | ~40 nH | **1,0 V** |
| capacitor a 1,75 mm do pino | ~2,5 nH | **62 mV** |

Um volt a menos num trilho de 3,3 V derruba o chip. 62 mV ninguém percebe.
**Mesma net, mesmos 3,3 V, comportamento completamente diferente conforme o
ponto da placa.** Em corrente contínua os dois pontos realmente são o mesmo nó;
em nanossegundos, não são. Por isso cada capacitor ficou a 1,75–2,0 mm do pino
que atende: a distância é o parâmetro de projeto, mais ainda que o valor.

### Segundo motivo: o capacitor também é um indutor

Mesmo que a distância não existisse, um capacitor só não daria conta. Todo
capacitor tem indutância própria (ESL, ~2 nH já contando a montagem), e isso
cria uma frequência de ressonância própria:

| componente | ressonância aproximada |
|---|---|
| 100 nF em 0603 | ~11 MHz |
| 10 µF em 0805 | ~1,1 MHz |

**Acima da ressonância, o capacitor se comporta como indutor** — a impedância
volta a subir e ele deixa de desacoplar. Daí a conclusão contraintuitiva: para
os picos rápidos, "um capacitor maior" é *pior*, não melhor, porque quanto maior
a capacitância, mais baixa a frequência de ressonância.

Cobrir de kHz a centenas de MHz exige valores diferentes, em paralelo e
espalhados. Em paralelo eles ainda dividem a indutância: dois iguais dão metade
da ESL, três dão um terço.

### O que cada um faz

| capacitor | onde | por quê |
|---|---|---|
| C3 10 µF + C4 100 nF | saída do regulador | o MCP1703 **exige** capacitor de saída para não oscilar; o C3 também absorve os pulsos do buzzer |
| C6 100 nF | VDD do MCU (pino 1) | picos do núcleo a 48 MHz |
| C7 100 nF | VDDIO2 do MCU (pino 17) | cada pino de alimentação tem caminho interno próprio e precisa do seu capacitor |
| C8 1 µF | MCU | reserva de volume para o chip todo |
| C9 100 nF + C10 1 µF | VDDA do MCU (pino 5) | alimentação analógica — ver abaixo |
| C12 100 nF | barômetro | pedido pelo datasheet, junto ao VDD |
| C13 100 nF | flash | gravar e apagar puxa ~25 mA em pulsos |

### O VDDA é um caso diferente

C9 e C10 não estão ali para fornecer corrente. Estão para **impedir que o ruído
chegue**.

O VDDA é a referência do conversor A/D, e as duas decisões que importam no voo
saem de medidas analógicas: a altitude, do barômetro, e a continuidade dos
ignitores e a tensão da bateria, do ADC. Ruído do núcleo digital de 48 MHz
entrando no VDDA vira erro de altitude ou alarme falso de ignitor desconectado.
Aqui os capacitores trabalham como filtro, não como reservatório.

Como o VDDA está ligado ao mesmo `+3V3`, a tolerância do regulador entra direto
nas medidas de tensão. Para precisão, o firmware deve medir a referência interna
(VREFINT) e corrigir com o valor de calibração de fábrica, em vez de supor
3,300 V exatos.

### Quando um capacitor bastaria

Numa placa de poucos milímetros, ou num circuito lento — um relógio de 32 kHz,
por exemplo, onde di/dt é desprezível e 40 nH não mudam nada. O caso aqui é o
oposto: MCU a 48 MHz, SPI a 12 MHz e 66 mm de placa.

Cada capacitor custa frações de centavo. É seguro barato contra a falha mais
difícil de depurar: a que só aparece às vezes — em voo, quando o buzzer toca ou
a flash grava.

---

## Medir a própria bateria

R1/R2 dividem o `VBAT` por 11 e entregam o resultado ao PA2. C5 filtra.

| VBAT | no ADC |
|---|---|
| 4 V | 0,36 V |
| 7,4 V (LiPo 2S) | 0,67 V |
| 9 V | 0,82 V |
| 16 V | 1,45 V |

A medida é tomada **antes** do D1, ou seja, é a tensão real da bateria, não a de
depois do diodo. Serve para avisar bateria fraca pelo buzzer antes do
lançamento. O preço é o divisor drenando VBAT/110 kΩ permanentemente: 67 µA a
7,4 V. Com a placa armada por 10 horas, são 0,67 mAh — desprezível em qualquer
bateria utilizável.

O mesmo divisor de 100 k/10 k aparece nos testes de continuidade (`SNS_A`,
`SNS_B`), o que torna a comparação direta: um ignitor presente faz `SNS_x` ficar
perto de `VB_SNS`; um ignitor ausente leva a leitura a zero.

---

## Proteções que existem

| ameaça | o que protege |
|---|---|
| ESD no conector USB | U5 (USBLC6-2SC6) junto ao conector |
| bateria e USB ligados juntos | D1/D2 impedem corrente entre as fontes |
| queda de tensão no disparo | C1 no `VBAT`; D1 isola o `VSYS` |
| MCU em reset ou sem firmware | R9/R13 de 100 k mantêm os MOSFETs desligados |
| regulador oscilando | C3/C4 na saída, como pede o datasheet |

## Proteções que faltam

**1. Crítico — o bootloader dispara o canal principal.** Não é um problema de
alimentação, mas é o que mais importa nesta placa. `FIRE_B` está no PA9, que o
bootloader da ROM configura como USART1_TX em push-pull com pull-up (AN2606
rev. 61, tabela 19); linha UART em repouso fica em nível alto e **liga o Q2**. O
bootloader roda com o JP1 fechado e também, sozinho, quando a flash está vazia
com BOOT0 em 0 (AN2606, padrão 6) — ou seja, na primeira energização de toda
placa nova. Correção: mover `FIRE_B` para o PB4. Até lá, gravar firmware só pelo
USB, sem bateria e sem ignitores.

**2. Alto — bateria invertida dispara os ignitores.** O D1 protege a lógica:
com `VBAT` negativo ele simplesmente bloqueia. Mas os ignitores estão antes dele.
Com a bateria ao contrário, a corrente encontra o caminho GND → diodo de corpo
do Q1/Q2 → ignitor → bateria, limitada só pela resistência do ignitor. São
ampères: **o ignitor acende**. O C1, eletrolítico, também sofre. Correção: um
MOSFET canal P em série na entrada da bateria (proteção de polaridade com queda
quase nula), ou um conector polarizado em vez do borne a parafuso.

**3. Médio — o Q3 do buzzer está no limite.** O CMT-8504 consome 150 mA a 5 V
(4 kHz, meio ciclo) e tem bobina de 12–18 Ω; a 3,3 V isso escala para ~100 mA. O
BSS138 tem alguns ohms de resistência de canal com 3,3 V no gate, o que rouba
tensão da bobina e reduz o volume. Trocar por AO3400A — o mesmo dos canais de
disparo — resolve e ainda reduz uma linha da lista de materiais.

**4. Baixo — não há proteção contra sobretensão no `VBAT`.** Acima de 16 V o
regulador é o primeiro a falhar. Um TVS de 18 V na entrada cobre picos.

**5. Não há chave na placa.** Bateria conectada significa placa ligada. O
pressuposto, como no EasyMini, é uma chave externa em série com a bateria, na
baia de eletrônica — que também é o jeito normal de armar o foguete na rampa.

---

## Fontes

- [AN2606, *STM32 microcontroller system memory boot mode*, rev. 61](https://kolegite.com/EE_library/application_notes/MCU/STM32/STM32%20microcontroller%20system%20memory%20boot%20mode.pdf)
  — tabela 19 (pinos do bootloader do STM32F04x) e tabela 2 (padrões de ativação).
- Datasheet do MCP1703 (Microchip DS20005122B) — entrada máxima, consumo próprio
  e capacitores exigidos.
- Datasheet do CMT-8504-100-SMT (Same Sky/CUI) — tensão nominal, consumo e
  resistência da bobina.
- Distâncias de desacoplamento medidas em `altimetro.kicad_pcb` com o módulo
  Python do KiCad.
