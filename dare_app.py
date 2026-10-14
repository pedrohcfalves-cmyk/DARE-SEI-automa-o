"""
DARE Automação — aplicativo com janela (interface gráfica).

Faz o mesmo que o modo terminal (dare_automacao.py): gera o DARE avulso, salva o PDF e o anexa
como documento externo no SEI, em lotes digitados ou lidos de uma planilha. Acrescenta a
limpeza da pasta dos PDFs e a aba de desempenho/diagnóstico.

Uso:  python dare_app.py        (ou o executável "DARE Automacao.exe")

Copyright (c) 2026. Todos os direitos reservados. Uso restrito a pessoas autorizadas pelo
titular (veja LICENCA.txt).
"""

import sys


def diagnostico_por_linha_de_comando() -> int:
    """
    "DARE Automacao.exe --diagnostico [arquivo.html]": gera o relatório de diagnóstico sem abrir a
    janela (útil para suporte). Devolve 0 se não houver problema grave.
    """
    from pathlib import Path

    from dare_auto import config, desempenho, logger

    logger.configurar(console=False)
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    destino = Path(argumentos[0]) if argumentos else config.BASE_DADOS / "diagnostico.html"
    itens = desempenho.diagnosticar()
    desempenho.gerar_relatorio_html(destino, diagnostico=itens)
    if sys.stdout is not None:
        for i in itens:
            print(f"[{i.status:5}] {i.grupo} · {i.nome}: {i.valor}")
        print(f"Relatório: {destino}")
    return 1 if any(i.status == desempenho.ERRO and i.nome == "Motor de automação" for i in itens) else 0


if __name__ == "__main__":
    if "--terminal" in sys.argv:  # o modo terminal antigo continua disponível
        import dare_automacao
        dare_automacao.main()
    elif "--diagnostico" in sys.argv:
        sys.exit(diagnostico_por_linha_de_comando())
    else:
        from dare_auto.gui.app import main
        main()
