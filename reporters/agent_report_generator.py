"""
에이전트 분석 보고서 생성기 - 단일 도메인 분석 결과 시각화 (HTML)
"""

import re
import base64
import logging
from datetime import datetime
from pathlib import Path
from io import BytesIO
from typing import Dict

try:
    import matplotlib
    from matplotlib import font_manager
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    korean_font_candidates = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'Noto Sans CJK KR']
    available_fonts = {font.name for font in font_manager.fontManager.ttflist}
    for font_name in korean_font_candidates:
        if font_name in available_fonts:
            plt.rcParams['font.family'] = font_name
            break
    else:
        plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

logger = logging.getLogger(__name__)

CSS = """
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css");
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg: #070816; --line: rgba(255,255,255,0.11); --text: #f9fafb;
    --sub: #9ca3af; --muted: #667085; --primary: #6366f1;
    --purple: #8b5cf6; --pink: #ec4899; --cyan: #38bdf8;
    --danger: #ef4444; --success: #22c55e;
}
body {
    font-family: "Pretendard", sans-serif;
    background:
        radial-gradient(circle at 18% 8%, rgba(139,92,246,0.3), transparent 32%),
        radial-gradient(circle at 88% 20%, rgba(236,72,153,0.2), transparent 30%),
        radial-gradient(circle at 70% 92%, rgba(56,189,248,0.16), transparent 32%),
        linear-gradient(135deg, #070816 0%, #0b1020 55%, #090916 100%);
    color: var(--text); min-height: 100vh; padding: 32px;
    overflow-x: hidden; animation: bgMove 12s ease-in-out infinite alternate;
}
body::before {
    content: ""; position: fixed; inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,0.82), transparent 82%);
    pointer-events: none; z-index: 0; animation: gridMove 18s linear infinite;
}
.wrapper { position: relative; z-index: 1; max-width: 1040px; margin: 0 auto; animation: pageEnter 0.7s ease both; }
.container {
    background: linear-gradient(180deg, rgba(17,24,39,0.96) 0%, rgba(15,23,42,0.98) 100%);
    border: 1px solid var(--line); border-radius: 18px; padding: 64px;
    box-shadow: 0 30px 100px rgba(0,0,0,0.56), inset 0 1px 0 rgba(255,255,255,0.06);
    backdrop-filter: blur(18px); animation: cardEnter 0.8s ease both;
}
.top-bar { display: flex; align-items: center; gap: 14px; margin-bottom: 48px; }
.logo {
    width: 46px; height: 46px; border-radius: 8px; flex-shrink: 0;
    background: linear-gradient(135deg, var(--primary), var(--purple));
    position: relative; animation: logoPulse 3s ease-in-out infinite;
}
.logo::after { content: ""; position: absolute; inset: 11px; border: 2px solid white; border-radius: 4px; }
.brand-title { font-weight: 700; font-size: 15px; }
.system-label { font-size: 11px; font-weight: 700; letter-spacing: 0.18em; color: #6b7280; }
.report-title { font-size: 42px; font-weight: 800; letter-spacing: -1.4px; margin-bottom: 10px; word-break: break-all; }
.report-meta { color: var(--sub); font-size: 15px; line-height: 1.7; }
.section { margin-top: 44px; animation: fadeUp 0.7s ease both; }
.section-title { font-size: 20px; font-weight: 800; margin-bottom: 18px; color: var(--text); letter-spacing: -0.3px; }
.trust-card {
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.22);
    border-left: 4px solid var(--primary); border-radius: 12px;
    padding: 32px; text-align: center; color: #c7d2fe;
}
.trust-score { font-size: 56px; font-weight: 900; margin: 12px 0; color: #fff; }
.trust-level { color: var(--sub); font-size: 17px; }
.score-breakdown { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 22px; }
.score-item {
    background: rgba(11,18,32,0.86); border: 1px solid var(--line);
    border-radius: 10px; padding: 20px; text-align: center; transition: 0.22s ease;
}
.score-item:hover { border-color: rgba(99,102,241,0.4); background: rgba(99,102,241,0.08); transform: translateY(-2px); }
.score-item-value { font-size: 32px; font-weight: 900; color: #c7d2fe; }
.score-item-label { font-size: 12px; color: var(--muted); margin-top: 6px; }
.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
.info-box {
    background: rgba(11,18,32,0.86); border: 1px solid var(--line);
    border-left: 4px solid var(--primary); border-radius: 8px;
    padding: 18px; margin-top: 12px; transition: 0.22s ease;
}
.info-box:hover { border-color: rgba(99,102,241,0.4); background: rgba(99,102,241,0.08); }
.info-box-title { font-weight: 800; color: #c7d2fe; margin-bottom: 7px; font-size: 12px; letter-spacing: 0.05em; }
.info-box-content { font-size: 14px; color: #d1d5db; word-break: break-all; }
.status-badge { display: inline-flex; padding: 5px 12px; border-radius: 999px; font-size: 12px; font-weight: 800; margin-right: 6px; }
.status-success { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2); color: #86efac; }
.status-danger  { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.2);  color: #fca5a5; }
.status-warning { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.2); color: #fcd34d; }
.analysis-section {
    background: rgba(11,18,32,0.86); border: 1px solid var(--line);
    border-radius: 10px; padding: 22px;
}
.analysis-text { white-space: pre-wrap; font-family: Consolas, monospace; font-size: 13px; line-height: 1.8; color: #d1d5db; }
.chart-container {
    text-align: center; margin-top: 18px;
    background: rgba(11,18,32,0.86); border: 1px solid var(--line);
    border-radius: 10px; padding: 20px;
}
.chart-container img { max-width: 100%; height: auto; border-radius: 8px; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; border-radius: 10px; overflow: hidden; }
th, td { padding: 14px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.07); font-size: 14px; }
thead { background: rgba(99,102,241,0.22); }
th { font-weight: 800; color: #e5e7eb; }
td { color: #d1d5db; }
tbody tr { transition: 0.2s; }
tbody tr:hover { background: rgba(99,102,241,0.08); }
.warn-box {
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2);
    border-left: 4px solid #f59e0b; border-radius: 8px;
    padding: 18px; margin-top: 12px; color: #fcd34d;
}
.coda-badge-uncertain {
    background: rgba(245,158,11,0.08); border-left-color: #f59e0b !important;
}
.footer { margin-top: 52px; padding-top: 24px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; text-align: center; }
@keyframes pageEnter { from { opacity:0; transform: translateY(18px) scale(0.985); } to { opacity:1; transform: translateY(0) scale(1); } }
@keyframes cardEnter  { from { opacity:0; transform: translateY(24px); } to { opacity:1; transform: translateY(0); } }
@keyframes fadeUp     { from { opacity:0; transform: translateY(14px); } to { opacity:1; transform: translateY(0); } }
@keyframes bgMove     { from { background-position: 0% 0%; } to { background-position: 20px 30px; } }
@keyframes gridMove   { from { background-position: 0 0; } to { background-position: 46px 46px; } }
@keyframes logoPulse  { 0%,100% { box-shadow: 0 0 0 rgba(99,102,241,0); } 50% { box-shadow: 0 0 28px rgba(99,102,241,0.45); } }
@media (max-width: 768px) {
    body { padding: 18px; }
    .container { padding: 32px 20px; }
    .report-title { font-size: 28px; }
    .score-breakdown, .info-grid { grid-template-columns: 1fr; }
}
</style>
"""


class AgentReportGenerator:
    """단일 도메인 분석 결과 HTML 보고서 생성"""

    def __init__(self, output_dir: str = "analysis_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"보고서 저장 경로: {self.output_dir}")

    def generate_report(self, domain: str, analysis_result: Dict,
                        trust_analysis: Dict, coda_result: Dict = None,
                        llm_result: Dict = None, category_result: Dict = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{domain.replace('.', '_')}_{timestamp}.html"
        filepath = self.output_dir / filename

        charts = self._generate_charts(coda_result or {}, category_result or {})
        html_content = self._generate_html(
            domain=domain,
            analysis_result=analysis_result,
            trust_analysis=trust_analysis,
            coda_result=coda_result or {},
            charts=charts,
            llm_result=llm_result or {},
            category_result=category_result or {}
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✅ 보고서 생성 완료: {filepath}")
        return str(filepath)

    def _extract_onion_domains(self, html_content: str, limit: int = 10) -> list:
        try:
            matches = re.findall(r'([a-z0-9\-]+\.onion)', html_content, re.IGNORECASE)
            unique = sorted(set(m.lower() for m in matches))
            return unique[:limit]
        except Exception:
            return []

    def _generate_charts(self, coda_result: Dict, category_result: Dict) -> Dict:
        charts = {}
        if not MATPLOTLIB_AVAILABLE:
            return charts
        try:
            if coda_result.get('all_probs'):
                charts['coda'] = self._create_bar_chart(
                    data=coda_result['all_probs'],
                    title='CoDA 범죄 카테고리 확률',
                    color='#ef4444'
                )
            cat_scores = category_result.get('category_scores', {})
            if cat_scores:
                charts['category'] = self._create_bar_chart(
                    data=cat_scores,
                    title='사이트 유형 분류 점수',
                    color='#6366f1'
                )
        except Exception as e:
            logger.error(f"차트 생성 오류: {e}")
        return charts

    def _save_chart(self, fig) -> str:
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=120,
                    facecolor='#111827', edgecolor='none')
        buf.seek(0)
        result = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return result

    def _create_bar_chart(self, data: Dict, title: str, color: str) -> str:
        try:
            labels = list(data.keys())
            values = [v * 100 if v <= 1.0 else float(v) for v in data.values()]

            fig_h = max(3, len(labels) * 0.6)
            fig, ax = plt.subplots(figsize=(8, fig_h))
            fig.patch.set_facecolor('#111827')
            ax.set_facecolor('#111827')

            bars = ax.barh(labels, values, color=color, alpha=0.82, height=0.55)

            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                        f'{val:.1f}%', va='center', ha='left', color='#f9fafb',
                        fontsize=9, fontweight='bold')

            ax.set_xlim(0, 115)
            ax.set_xlabel('%', color='#9ca3af', fontsize=10, fontweight='bold')
            ax.set_title(title, color='#f9fafb', fontsize=12, fontweight='bold', pad=12)
            ax.tick_params(colors='#9ca3af')
            for label in ax.get_yticklabels():
                label.set_fontweight('bold')
                label.set_color('#f9fafb')
            for label in ax.get_xticklabels():
                label.set_fontweight('bold')
            for spine in ('top', 'right'):
                ax.spines[spine].set_visible(False)
            ax.spines['bottom'].set_color('#374151')
            ax.spines['left'].set_color('#374151')
            ax.xaxis.label.set_color('#9ca3af')
            ax.yaxis.label.set_color('#9ca3af')
            fig.tight_layout()
            return self._save_chart(fig)
        except Exception as e:
            logger.error(f"막대 차트 오류: {e}")
            return ""

    def _generate_html(self, domain: str, analysis_result: Dict, trust_analysis: Dict,
                       coda_result: Dict, charts: Dict, llm_result: Dict,
                       category_result: Dict = None) -> str:
        accessibility = analysis_result.get('accessibility', {})
        indexing = analysis_result.get('indexing', {})
        html_collected = analysis_result.get('html_collected', False)

        trust_level_ko = {
            'HIGHLY_TRUSTWORTHY': '매우 높음', 'TRUSTWORTHY': '높음',
            'SUSPICIOUS': '중간 (의심)', 'UNTRUSTED': '낮음 (위험)',
            'UNREACHABLE': '분석 불가'
        }.get(trust_analysis.get('trust_level', ''), '알 수 없음')

        def badge(ok, yes='접근 가능', no='접근 불가'):
            cls = 'status-success' if ok else 'status-danger'
            return f'<span class="status-badge {cls}">{yes if ok else no}</span>'

        now = datetime.now()
        ts = now.strftime('%Y년 %m월 %d일 %H:%M:%S')
        ts_f = now.strftime('%Y-%m-%d %H:%M:%S')

        h = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>분석 보고서 - {domain}</title>
{CSS}
</head>
<body>
<div class="wrapper"><div class="container">

<div class="top-bar">
  <div class="logo"></div>
  <div>
    <div class="brand-title">Darkweb Analyzer</div>
    <div class="system-label">SECURITY ANALYSIS SYSTEM</div>
  </div>
</div>

<div class="report-title">{domain}</div>
<div class="report-meta">생성 일시: {ts}</div>
"""

        # 경고
        if analysis_result.get('analysis_warning'):
            h += f'<div class="warn-box" style="margin-top:24px;">⚠️ {analysis_result["analysis_warning"]}</div>'

        # 신뢰도
        sb = trust_analysis['score_breakdown']
        h += f"""
<div class="section">
  <div class="section-title">종합 신뢰도 분석</div>
  <div class="trust-card">
    <div>신뢰도 점수</div>
    <div class="trust-score">{trust_analysis['total_score']}/100</div>
    <div class="trust-level">{trust_level_ko}</div>
  </div>
  <div class="score-breakdown">
    <div class="score-item"><div class="score-item-value">{sb['accessibility']['score']}</div><div class="score-item-label">접근성 (40점)</div></div>
    <div class="score-item"><div class="score-item-value">{sb['indexing']['score']}</div><div class="score-item-label">색인 (30점)</div></div>
    <div class="score-item"><div class="score-item-value">{sb['content']['score']}</div><div class="score-item-label">콘텐츠 (30점)</div></div>
  </div>
</div>
"""

        # 상세 분석
        h += f"""
<div class="section">
  <div class="section-title">상세 분석</div>
  <div class="analysis-section"><div class="analysis-text">{trust_analysis.get('detailed_analysis','')}</div></div>
</div>
"""

        # 접근성
        response_time = round(accessibility.get('response_time') or 0, 2)
        h += f"""
<div class="section">
  <div class="section-title">접근성 정보</div>
  <div class="info-grid">
    <div class="info-box"><div class="info-box-title">HTML 수집</div><div class="info-box-content">{badge(html_collected, '수집됨', '미수집')}</div></div>
    <div class="info-box"><div class="info-box-title">HTTP 상태</div><div class="info-box-content">{accessibility.get('status_code','N/A')} {badge(accessibility.get('is_accessible'))}</div></div>
    <div class="info-box"><div class="info-box-title">응답 시간</div><div class="info-box-content">{response_time}초</div></div>
  </div>
"""
        if accessibility.get('fallback_domain'):
            h += f'<div class="info-box"><div class="info-box-title">재검증</div><div class="info-box-content">{accessibility["fallback_domain"]} {badge(accessibility.get("fallback_accessible"), "성공", "실패")}</div></div>'
        h += '</div>'

        # 검색 색인
        ahmia_b = badge(indexing.get('ahmia_found'), '검색됨', '미발견')
        ddgo_b  = badge(indexing.get('duckduckgo_found'), '검색됨', '미발견')
        h += f"""
<div class="section">
  <div class="section-title">검색 색인 정보</div>
  <table>
    <thead><tr><th>엔진</th><th>상태</th><th>결과</th></tr></thead>
    <tbody>
      <tr><td>Ahmia</td><td>{ahmia_b}</td><td>{indexing.get('ahmia_results',0)}건</td></tr>
      <tr><td>DuckDuckGo</td><td>{ddgo_b}</td><td>{'True' if indexing.get('duckduckgo_found') else 'False'}</td></tr>
    </tbody>
  </table>
"""
        extracted_urls = indexing.get('extracted_urls', [])
        if extracted_urls:
            urls_html = '<br>'.join(extracted_urls[:15])
            h += f'<div class="info-box"><div class="info-box-title">상대 경로 ({len(extracted_urls)}개)</div><div class="info-box-content" style="font-size:12px;max-height:240px;overflow-y:auto;">{urls_html}</div></div>'

        if html_collected:
            onion_domains = self._extract_onion_domains(analysis_result.get('html_content', ''))
            if onion_domains:
                h += f'<div class="info-box"><div class="info-box-title">페이지 내 .onion 도메인 ({len(onion_domains)}개)</div><div class="info-box-content" style="font-size:12px;">' + '<br>'.join(onion_domains) + '</div></div>'
        h += '</div>'

        # 사이트 유형 분류 (BART)
        category_result = category_result or {}
        h += '<div class="section"><div class="section-title">사이트 유형 분류</div>'
        if not html_collected:
            h += '<div class="info-box"><div class="info-box-content">HTML 미수집으로 분석을 수행하지 않았습니다.</div></div>'
        elif category_result.get('skip_reason'):
            h += '<div class="info-box"><div class="info-box-content">분류 스킵됨</div></div>'
        else:
            primary = category_result.get('primary_category', 'unknown').replace('_', ' ').title()
            secondary = category_result.get('secondary_category')
            conf = round(category_result.get('confidence', 0) * 100, 1)
            h += f'<div class="info-box"><div class="info-box-title">주요 유형</div><div class="info-box-content"><span style="font-size:18px;font-weight:900;color:#c7d2fe;">{primary}</span> &nbsp;{conf}%</div></div>'
            if secondary:
                h += f'<div class="info-box" style="margin-top:10px;"><div class="info-box-title">보조 유형</div><div class="info-box-content">{secondary.replace("_"," ").title()}</div></div>'
            if charts.get('category'):
                cat_chart = charts['category']
                h += f'<div class="chart-container"><img src="data:image/png;base64,{cat_chart}" alt="사이트 유형 분류 차트"></div>'
        h += '</div>'

        # CoDA 분류
        h += '<div class="section"><div class="section-title">CoDA 범죄 카테고리 분류</div>'
        if not html_collected:
            h += '<div class="info-box"><div class="info-box-content">HTML 미수집으로 분석을 수행하지 않았습니다.</div></div>'
        elif not coda_result.get('available'):
            h += '<div class="info-box warn-box"><div class="info-box-content">⚠️ 학습된 모델 없음 — <code>python3 analyzers/train_coda_classifier.py</code> 실행 필요</div></div>'
        else:
            cat = coda_result.get('category', 'unknown').upper()
            conf = round(coda_result.get('confidence', 0) * 100, 1)
            uncertain = coda_result.get('uncertain', False)
            uncertain_note = ' &nbsp;<span class="status-badge status-warning">⚠️ 분류 불확실</span>' if uncertain else ''
            box_cls = 'coda-badge-uncertain' if uncertain else ''
            h += f'<div class="info-box {box_cls}"><div class="info-box-title">분류 결과</div><div class="info-box-content"><span style="font-size:20px;font-weight:900;color:#c7d2fe;">{cat}</span> &nbsp;{conf}%{uncertain_note}</div></div>'

            all_probs = coda_result.get('all_probs', {})
            if all_probs:
                probs_html = ' &nbsp;|&nbsp; '.join(
                    f'<b>{k.upper()}</b>: {round(v*100,1)}%'
                    for k, v in list(all_probs.items())[:5]
                )
                h += f'<div class="info-box" style="margin-top:10px;"><div class="info-box-title">상위 5개 확률</div><div class="info-box-content" style="font-size:13px;">{probs_html}</div></div>'
            if charts.get('coda'):
                coda_chart = charts['coda']
                h += f'<div class="chart-container"><img src="data:image/png;base64,{coda_chart}" alt="CoDA 범죄 카테고리 차트"></div>'
        h += '</div>'

        # LLM 분석
        if llm_result and llm_result.get('success'):
            risk = llm_result.get('risk_level', '')
            risk_cls = {'낮음': 'status-success', '중간': 'status-warning', '높음': 'status-danger', '매우높음': 'status-danger'}.get(risk, '')
            features = llm_result.get('notable_features', [])
            features_html = ('<ul style="margin:8px 0 0 16px;">' + ''.join(f'<li style="font-size:13px;margin-bottom:4px;">{f}</li>' for f in features) + '</ul>') if features else ''
            h += f"""
<div class="section">
  <div class="section-title">AI 사이트 분석 (Claude)</div>
  <div class="info-grid">
    <div class="info-box"><div class="info-box-title">사이트 유형</div><div class="info-box-content">{llm_result.get('site_type') or '-'}</div></div>
    <div class="info-box"><div class="info-box-title">주요 언어</div><div class="info-box-content">{llm_result.get('language') or '-'}</div></div>
  </div>
  <div class="info-box"><div class="info-box-title">목적</div><div class="info-box-content">{llm_result.get('purpose') or '-'}</div></div>
  <div class="info-box"><div class="info-box-title">요약</div><div class="info-box-content">{llm_result.get('summary') or '-'}</div></div>
  <div class="info-box"><div class="info-box-title">AI 위험도 평가</div><div class="info-box-content"><span class="status-badge {risk_cls}">{risk}</span> {llm_result.get('risk_reason') or ''}</div></div>
  {f'<div class="info-box"><div class="info-box-title">주목할 특징</div><div class="info-box-content">{features_html}</div></div>' if features_html else ''}
  <div style="font-size:11px;color:var(--muted);margin-top:10px;">모델: {llm_result.get('model_used') or ''}</div>
</div>
"""
        elif llm_result and not llm_result.get('success'):
            err = llm_result.get('error', '')
            if err not in ('HTML 미수집', 'API 키 미설정'):
                h += f'<div class="section"><div class="section-title">AI 사이트 분석 (Claude)</div><div class="info-box"><div class="info-box-content">분석 실패: {err}</div></div></div>'

        # 결론
        coda_summary = ''
        if coda_result and coda_result.get('available'):
            uncertain_txt = ' (불확실)' if coda_result.get('uncertain') else ''
            coda_summary = f'<p><strong>CoDA 분류:</strong> {coda_result.get("category","unknown").upper()}{uncertain_txt}</p>'

        h += f"""
<div class="section">
  <div class="section-title">조사 결론</div>
  <div class="analysis-section">
    <p><strong>도메인:</strong> {domain}</p>
    <p><strong>신뢰도:</strong> {trust_level_ko} ({trust_analysis['total_score']}/100)</p>
    <p><strong>접근성:</strong> {'가능' if accessibility.get('is_accessible') else '불가'}</p>
    <p><strong>HTML 수집:</strong> {'수집됨' if html_collected else '미수집'}</p>
    <p><strong>색인 상태:</strong> {'공개' if indexing.get('combined_found') else '은닉'}</p>
    {coda_summary}
  </div>
</div>

<div class="footer">자동 생성 | {ts_f}</div>

</div></div>
</body></html>
"""
        return h
