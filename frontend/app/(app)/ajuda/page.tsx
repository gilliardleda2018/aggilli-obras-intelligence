import Link from "next/link";
import type {ReactNode} from "react";
import {PageHead} from "../../../components/app-shell";
import {Card} from "../../../components/ui";

/** Plain-language manual: what each part of the system is for and how to feed it. Static content, no API calls. */
function Topic({title, href, children}: {title: string; href?: string; children: ReactNode}) {
  return <details className="help-topic">
    <summary>{title}{href && <Link className="link" href={href}>abrir</Link>}</summary>
    <div className="help-body">{children}</div>
  </details>;
}

export default function Help() {
  return <>
    <PageHead eyebrow="Ajuda" title="Como usar o sistema"
              subtitle="Explicação simples de cada parte e de como alimentar os dados. Toque em um assunto para abrir."/>

    <div className="stack">
      <Card title="Comece por aqui">
        <ol className="help-steps">
          <li><b>Entre</b> com seu usuário. O que você vê depende do seu perfil (dono, engenheiro, campo ou só consulta).</li>
          <li><b>Escolha a obra</b> em <Link className="link" href="/obras">Obras</Link>. Cada obra tem sua página com tudo dela.</li>
          <li><b>Alimente</b> no dia a dia: diário com fotos, notas e recibos, medições e materiais.</li>
          <li><b>Acompanhe</b> no <Link className="link" href="/simples">Modo simples</Link> (resumo para o dono) ou na
            <Link className="link" href="/"> Visão geral</Link> (painel completo).</li>
        </ol>
        <p className="help-note">Regra de ouro: <b>o sistema só mostra o que foi lançado</b>. Obra sem lançamento aparece
          vazia ou em 0% — não é defeito, é falta de dado.</p>
      </Card>

      <Card title="Como alimentar (o que lançar e onde)">
        <Topic title="1. Etapas da obra e medições — é isso que gera o percentual de avanço" href="/medicoes">
          <p>Em <b>Medições</b>, escolha a obra e cadastre cada <b>etapa</b> (ex.: Fundação, Alvenaria, Cobertura):</p>
          <ul>
            <li><b>Nome</b> e <b>unidade</b> (m², m³, un, verba…).</li>
            <li><b>Quantidade prevista</b>: o total da etapa no projeto (ex.: 320 m² de alvenaria).</li>
            <li><b>Peso</b>: quanto a etapa vale no total da obra. A soma dos pesos deve dar <b>100%</b>.</li>
          </ul>
          <p>Depois, conforme o serviço anda, use <b>Lançar medição</b> com a quantidade executada. Um engenheiro ou o
            dono <b>aprova</b>. Só medição aprovada conta no avanço.</p>
          <p>A <b>previsão de término</b> aparece quando os pesos somam 100% e há medições aprovadas em pelo menos 3 datas.</p>
        </Topic>
        <Topic title="2. Diário de obra — o que foi feito no dia, com fotos" href="/diario">
          <p>Escolha a obra, marque o tempo (sol, nublado, chuva), escreva em poucas palavras o que foi feito e tire as fotos
            pelo celular. Pode ligar cada foto a uma etapa.</p>
          <p>A localização do celular vai junto: o sistema mostra se a foto foi tirada <b>na obra</b> ou <b>fora dela</b>.
            Para isso a obra precisa ter a localização confirmada (página da obra → Localização).</p>
        </Topic>
        <Topic title="3. Notas e recibos — fotografe e o sistema lê" href="/documentos">
          <p>Fotografe a nota fiscal, o recibo, o orçamento ou o comprovante. O sistema lê fornecedor, valor, data e itens e
            sugere a obra pelo GPS de onde a foto foi tirada.</p>
          <p>Você <b>confere e confirma</b>. Só depois disso o gasto entra na obra. Orçamento fica guardado sem virar gasto;
            comprovante entra como pago. Nota repetida é avisada.</p>
          <p>Dica: foto de frente, documento inteiro, bem iluminado.</p>
        </Topic>
        <Topic title="4. Materiais — estoque e consumo" href="/materiais">
          <p>Cadastre os materiais de cada obra e registre <b>entradas</b> (compras) e <b>saídas</b> (consumo). O sistema calcula
            o custo médio e avisa quando o estoque deve acabar.</p>
        </Topic>
        <Topic title="5. Importar planilha — para trazer muita coisa de uma vez" href="/importar">
          <p>Envie a planilha de <b>custos</b>, <b>FOPAG</b> ou <b>medições</b> (Excel ou CSV). O sistema reconhece as colunas,
            a obra e a categoria de cada linha e mostra uma <b>prévia</b>. Nada é gravado até você confirmar. Enviar a mesma
            planilha de novo não duplica.</p>
          <p>A planilha de medições lança quantidades em etapas que <b>já estão cadastradas</b> na obra.</p>
        </Topic>
        <Topic title="6. Localização da obra" >
          <p>Na página da obra, abra <b>Localização</b>, busque o endereço e confirme o ponto no mapa (ou use o GPS estando
            na obra). Isso habilita o mapa, o Street View e a conferência das fotos e notas.</p>
        </Topic>
        <Topic title="Obras novas">
          <p>O cadastro de uma obra nova ainda é feito pela equipe de implantação. Peça informando nome, município e endereço.</p>
        </Topic>
      </Card>

      <Card title="Como acompanhar (o que cada tela mostra)">
        <Topic title="Modo simples" href="/simples"><p>Resumo em linguagem direta para o dono: o que precisa de atenção hoje,
          quanto vai pagar na semana e como cada obra anda.</p></Topic>
        <Topic title="Visão geral" href="/"><p>Painel completo: programação da semana, mão de obra, obrigações em aberto e saldo
          de contratos.</p></Topic>
        <Topic title="Inteligência" href="/inteligencia"><p>Previsões de término, custo final e caixa de cada obra, calculadas
          a partir do que foi lançado. Quando falta dado, a tela diz exatamente o quê.</p></Topic>
        <Topic title="Alertas" href="/alertas"><p>Avisos automáticos: gasto fora do padrão, pagamento sem comprovante, medição
          parada, previsão de atraso. Marque como resolvido quando tratar.</p></Topic>
        <Topic title="Mapa" href="/mapa"><p>Todas as obras no mapa, com cor por situação.</p></Topic>
        <Topic title="FOPAG semanal" href="/fopag"><p>Pagamentos programados da semana por fornecedor, equipe e obra.</p></Topic>
        <Topic title="Contratos e obrigações" href="/financeiro"><p>Empreitadas, adiantamentos e o que ainda falta pagar.</p></Topic>
        <Topic title="Conciliação" href="/conciliacao"><p>Compara o que era devido, o que foi programado e o que tem
          comprovante. Nada é dado como pago sem comprovante.</p></Topic>
        <Topic title="Atividades" href="/atividades"><p>O último relato de cada frente de obra.</p></Topic>
        <Topic title="Relatórios" href="/relatorios"><p>Relatórios e planilhas prontos para imprimir ou enviar.</p></Topic>
      </Card>

      <Card title="Dúvidas comuns">
        <Topic title="Por que a obra está em 0% ou “sem previsão”?"><p>Faltam etapas cadastradas ou medições aprovadas. Veja o
          item 1 de “Como alimentar”. A própria tela lista o que falta.</p></Topic>
        <Topic title="A foto aparece “fora da obra”"><p>Ou a foto foi tirada longe do endereço, ou a localização da obra está
          errada. Confira em Localização.</p></Topic>
        <Topic title="O valor lido da nota está errado"><p>Corrija no formulário antes de confirmar. O sistema nunca lança
          sozinho.</p></Topic>
        <Topic title="Lancei algo errado"><p>Medições e documentos passam por aprovação. Se já foi aprovado, fale com o
          responsável (dono ou administrador) para corrigir — tudo fica registrado no histórico.</p></Topic>
      </Card>
    </div>
  </>;
}
