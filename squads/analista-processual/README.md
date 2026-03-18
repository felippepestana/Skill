# Squad Analista-Processual

Conjunto de agentes especializados em análise de processos organizacionais.

## Agentes

| Agente | Responsabilidade |
|---|---|
| **Coordenador** | Orquestra o squad e consolida os resultados |
| **Mapeador** | Mapeia etapas, atores, entradas e saídas |
| **Avaliador** | Avalia riscos, gargalos e conformidade |
| **Documentador** | Gera o relatório final em Markdown |

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Passando o processo como argumento
python squad.py "Processo de onboarding de novos funcionários: RH abre vaga, seleciona candidatos..."

# Passando via stdin
cat processo.txt | python squad.py

# Modo interativo
python squad.py
```

## Saída

O squad entrega um relatório Markdown com:

- **Mapeamento** do processo (fluxo, atores, decisões)
- **Avaliação** (gargalos, riscos, score de maturidade)
- **Relatório executivo** com roadmap de melhorias
