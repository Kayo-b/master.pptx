from __future__ import annotations

import unittest

from pipeline.wikipedia import parse_wikipedia_evidence_html, parse_wikipedia_references_html


HTML = """
<html>
  <body>
    <div class="mw-parser-output">
      <p>
        Entre os mais expostos, estavam a Amprev do Amapá (400 milhões de reais investidos)
        <sup class="reference"><a href="#cite_note-60">[60]</a></sup>.
      </p>
      <h2>Referências</h2>
    </div>
    <ol class="references">
      <li id="cite_note-1">
        <span class="mw-cite-backlink"><a href="#cite_ref-1">↑</a></span>
        <cite>Banco Central determina intervenção</cite>
        <a class="external" href="https://www.gov.br/bcb/noticia">link</a>
        2024
      </li>
      <li id="cite_note-60">
        <span class="mw-cite-backlink"><a href="#cite_ref-60">↑</a></span>
        <cite>Banco Master recebeu investimentos de 18 fundos previdenciários, confira a lista</cite>
        <a class="external" href="https://www.infomoney.com.br/mercados/banco-master-recebeu-investimentos-de-18-fundos-previdenciarios-confira-lista/">ler</a>
      </li>
      <li id="cite_note-2">
        <span class="mw-cite-backlink"><a href="#cite_ref-2">↑</a></span>
        <cite>Reportagem do Valor</cite>
        <a class="external" href="https://valor.globo.com/materia">ler</a>
      </li>
    </ol>
  </body>
</html>
"""

MULTI_NOTE_HTML = """
<html>
  <body>
    <div class="mw-parser-output">
      <p>
        No dia 19 de agosto de 2025, com 14 votos favoráveis e 7 contra, a câmara legislativa do Distrito Federal aprovou a compra de 49% das ações ordinárias do Banco Master.
        <sup class="reference"><a href="#cite_note-67">[67]</a></sup>
        O deputado distrital da oposição Fábio Félix alertou para o risco ao orçamento público do DF.
        <sup class="reference"><a href="#cite_note-68">[68]</a></sup>
      </p>
      <h2>Referências</h2>
    </div>
    <ol class="references">
      <li id="cite_note-67">
        <span class="mw-cite-backlink"><a href="#cite_ref-67">↑</a></span>
        <cite>Aprovação da compra pela CLDF</cite>
        <a class="external" href="https://exemplo.com/cldf-aprova-compra">ler</a>
      </li>
      <li id="cite_note-68">
        <span class="mw-cite-backlink"><a href="#cite_ref-68">↑</a></span>
        <cite>Declaração de Fábio Félix</cite>
        <a class="external" href="https://exemplo.com/fabio-felix-alerta">ler</a>
      </li>
    </ol>
  </body>
</html>
"""


class WikipediaParserTestCase(unittest.TestCase):
    def test_parse_wikipedia_references_html(self) -> None:
        references = parse_wikipedia_references_html(HTML, "https://pt.wikipedia.org/wiki/Teste")
        self.assertEqual(len(references), 3)
        self.assertEqual(references[0]["tipo"], "documento_oficial")
        self.assertEqual(references[1]["id"], "wikipedia_ref_60")
        self.assertEqual(references[2]["titulo"], "Reportagem do Valor")

    def test_parse_wikipedia_evidence_html_links_claim_to_note(self) -> None:
        evidence = parse_wikipedia_evidence_html(HTML, "https://pt.wikipedia.org/wiki/Teste")
        linked_reference = evidence["referencias_vinculadas"][0]
        self.assertEqual(linked_reference["numero_nota"], "60")
        self.assertEqual(
            linked_reference["referencia_correspondente"]["url"],
            "https://www.infomoney.com.br/mercados/banco-master-recebeu-investimentos-de-18-fundos-previdenciarios-confira-lista/",
        )
        self.assertIn("Amprev do Amapá", linked_reference["trecho_artigo"])
        self.assertEqual(linked_reference["claim_estruturada"]["tipo"], "investimento")

    def test_parse_wikipedia_evidence_html_splits_paragraph_by_note(self) -> None:
        evidence = parse_wikipedia_evidence_html(MULTI_NOTE_HTML, "https://pt.wikipedia.org/wiki/Teste")
        self.assertEqual(len(evidence["referencias_vinculadas"]), 2)
        self.assertEqual(evidence["referencias_vinculadas"][0]["numero_nota"], "67")
        self.assertIn("câmara legislativa do Distrito Federal aprovou a compra", evidence["referencias_vinculadas"][0]["trecho_artigo"])
        self.assertEqual(evidence["referencias_vinculadas"][1]["numero_nota"], "68")
        self.assertIn("Fábio Félix alertou", evidence["referencias_vinculadas"][1]["trecho_artigo"])


if __name__ == "__main__":
    unittest.main()
