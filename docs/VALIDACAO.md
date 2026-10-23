# Validação — DadosLab 0.1.0

O relatório final desta entrega registra somente verificações realmente executadas. Resultados de Linux, Wine e Windows nativo devem ser distinguidos; Wine não substitui uma validação em uma instalação real de Windows.

## Resultados observados em 23/10/2026

- Instalação em ambiente Python 3.12 isolado das dependências declaradas.
- Motor C++ compilado em Linux com G++ 13.3, C++20, otimização e avisos tratados como erros.
- Classe Java compilada para Java 17 e executada em OpenJDK 17.0.20.
- `QT_QPA_PLATFORM=offscreen python -m pytest -q`: **29 testes passaram**.
- Verificação de 100.000 resultados C++ dentro de 1..6, contagens consistentes, sem usar p-valor aleatório como condição de aprovação.
- Interface Qt executada de verdade em modo offscreen: lançamento animado, lote, registro físico, alternância de origem e exportações testados.
- Captura real inspecionada visualmente após uma simulação de 1.000 lançamentos. A captura é do Linux em offscreen; não é uma execução Windows nem um mockup.
- Motor `dice.dll` e inicializador `DadosLab.exe` compilados por MinGW-w64 x86-64 em Linux. Ambos identificados como PE32+ Windows x64.
- Distribuição portátil montada com Python embutível Windows, wheels Windows e runtime Java Windows incluídos; inventário e SHA-256 dos downloads no pacote.
- **Execução nativa em Windows: não realizada neste ambiente.** A tentativa suplementar de usar Wine foi bloqueada porque o ambiente não permite o socket necessário ao wineserver; não houve resultado de execução Windows/Wine para afirmar.
- Workflow de build Windows preparado; sem execução remota observada nesta entrega.

Na preparação para o GitHub, o workflow passou a obter o caminho real do MSYS2 pela saída da action. Os comandos de compilação também incluem o diretório do compilador no PATH dos subprocessos, para permitir a resolução de suas ferramentas e DLLs. Esses ajustes não alteram o motor ou os cálculos estatísticos; a execução Windows continua sujeita à verificação do workflow e do ambiente de destino.

Os testes e a inspeção de formato PE não substituem abrir o pacote em Windows 10/11 x64. Se houver falha nessa etapa, `Diagnosticar.cmd` exibe detalhes para investigação.

Verificações implementadas: ABI C++, limites, contagens conferidas em Python/C++/Java, referências estatísticas conhecidas, amostras vazias/esparsas, rejeição de valores inválidos, persistência e separação de sessões, orientação das seis faces, animação, lote, troca de face, modo físico e exportação CSV/PNG/TXT.

Não são critérios de aprovação: obter um p-valor alto numa sequência aleatória, provar ausência de viés, demonstrar aceleração ou certificar a animação como física real. O gerador é pseudoaleatório e as conclusões são exploratórias.
