"""
에이전트 분석 보고서 생성기 - 단일 도메인 분석 결과 시각화 (HTML)
"""

import json
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
    korean_font_candidates = [
        'Malgun Gothic',
        'AppleGothic',
        'NanumGothic',
        'Noto Sans CJK KR',
        'Noto Sans KR',
        'Nanum Gothic'
    ]
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


class AgentReportGenerator:
    """단일 도메인 분석 결과 HTML 보고서 생성"""
    
    def __init__(self, output_dir: str = "analysis_reports"):
        """
        Args:
            output_dir: 보고서 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"보고서 저장 경로: {self.output_dir}")
    
    def generate_report(self, domain: str, analysis_result: Dict,
                       trust_analysis: Dict, coda_result: Dict = None,
                       llm_result: Dict = None) -> str:
        """
        종합 분석 보고서 생성

        Args:
            domain: 분석 대상 도메인
            analysis_result: 서버 분석 결과
            trust_analysis: 신뢰도 점수 분석
            coda_result: CoDA 학습 분류기 결과
            llm_result: Claude LLM 사이트 요약 결과

        Returns:
            생성된 보고서 파일 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_report_{domain.replace('.', '_')}_{timestamp}.html"
        filepath = self.output_dir / filename

        logger.info(f"보고서 생성 중: {domain}")

        # 차트 생성 (신뢰도 레이더만)
        charts = self._generate_charts(trust_analysis, {}, {})

        # HTML 생성
        html_content = self._generate_html(
            domain=domain,
            analysis_result=analysis_result,
            trust_analysis=trust_analysis,
            coda_result=coda_result or {},
            charts=charts,
            llm_result=llm_result or {}
        )

        # 파일 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✅ 보고서 생성 완료: {filepath}")

        return str(filepath)
    
    def _extract_onion_domains(self, html_content: str, limit: int = 10) -> list:
        """
        HTML 콘텐츠에서 어니언 도메인 추출
        
        Args:
            html_content: HTML 콘텐츠
            limit: 최대 추출 개수
        
        Returns:
            추출된 어니언 도메인 리스트
        """
        try:
            import re
            
            # .onion 도메인 패턴
            pattern = r'([a-z0-9\-]+\.onion)'
            
            # 모든 도메인 찾기
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            
            if not matches:
                return []
            
            # 중복 제거 및 소문자로 통일
            unique_domains = list(set([domain.lower() for domain in matches]))
            
            # 정렬 및 제한
            unique_domains.sort()
            
            logger.info(f"HTML에서 {len(unique_domains)}개의 어니언 도메인 추출")
            
            return unique_domains[:limit]
        
        except Exception as e:
            logger.error(f"어니언 도메인 추출 중 오류: {str(e)}")
            return []
    
    def _generate_charts(self, trust_analysis: Dict, content_analysis: Dict,
                        category_result: Dict) -> Dict:
        """차트 생성"""
        charts = {}
        
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib 미설치: 차트 미포함")
            return charts
        
        try:
            # 1. 신뢰도 레이더 차트
            charts['trust_radar'] = self._create_trust_radar_chart(trust_analysis)
            
            # 2. 불법 콘텐츠 카테고리 분포
            charts['illegal_categories'] = self._create_illegal_categories_chart(content_analysis)
            
            # 3. 카테고리 신뢰도
            charts['category_confidence'] = self._create_category_confidence_chart(category_result)
            
        except Exception as e:
            logger.error(f"차트 생성 중 오류: {str(e)}")
        
        return charts
    
    def _create_trust_radar_chart(self, trust_analysis: Dict) -> str:
        """신뢰도 그래프"""
        try:
            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection='polar'))
            
            scores = {
                '접근성': trust_analysis['score_breakdown']['accessibility']['percentage'],
                '색인 신뢰도': trust_analysis['score_breakdown']['indexing']['percentage'],
                '콘텐츠 신뢰도': trust_analysis['score_breakdown']['content']['percentage']
            }
            
            categories = list(scores.keys())
            values = list(scores.values())
            
            angles = [i / len(categories) * 2 * 3.14159 for i in range(len(categories))]
            values += values[:1]
            angles += angles[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, color='#00A8FF')
            ax.fill(angles, values, alpha=0.25, color='#00A8FF')
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=10)
            ax.set_ylim(0, 100)
            ax.set_title('신뢰도 점수 분석', size=12, weight='bold', pad=20)
            ax.grid(True)
            
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            return image_base64
        
        except Exception as e:
            logger.error(f"신뢰도 차트 생성 오류: {str(e)}")
            return ""
    
    def _create_illegal_categories_chart(self, content_analysis: Dict) -> str:
        """불법 콘텐츠 카테고리 신뢰도 분포"""
        try:
            categories = content_analysis.get('categories', {})

            found_categories = {}
            for category_name, category_data in categories.items():
                if not category_data.get('found'):
                    continue

                # DarkBERT+키워드 결합 점수 우선, 없으면 darkbert 점수 사용
                score = category_data.get('combined_score')
                if score is None:
                    score = category_data.get('darkbert_score', 0)

                if score and score > 0:
                    found_categories[category_name] = float(score) * 100
            
            if not found_categories:
                return ""
            
            fig, ax = plt.subplots(figsize=(8, 6))

            top_scores = sorted(found_categories.items(), key=lambda x: x[1], reverse=True)
            cat_names = [name.replace('_', ' ').title() for name, _ in top_scores]
            confidences = [score for _, score in top_scores]
            colors = [
                '#FF6B6B', '#FFA06B', '#FFD93D', '#6BCB77', '#4D96FF',
                '#B28DFF', '#4DD0E1', '#FF8FAB', '#8D99AE', '#06D6A0'
            ]
            colors = (colors * ((len(cat_names) // len(colors)) + 1))[:len(cat_names)]
            
            bars = ax.barh(cat_names, confidences, color=colors)
            
            for i, bar in enumerate(bars):
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{width:.1f}%', ha='left', va='center', fontsize=10, weight='bold')
            
            ax.set_xlabel('신뢰도 (%)', fontsize=11)
            ax.set_xlim(0, 100)
            ax.set_title('불법 콘텐츠 카테고리 신뢰도', fontsize=12, weight='bold', pad=15)
            ax.grid(axis='x', alpha=0.3)
            ax.invert_yaxis()
            
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            return image_base64
        
        except Exception as e:
            logger.error(f"불법 카테고리 차트 생성 오류: {str(e)}")
            return ""
    
    def _create_category_confidence_chart(self, category_result: Dict) -> str:
        """카테고리별 신뢰도"""
        try:
            category_scores = category_result.get('category_scores', {})
            
            top_scores = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            
            if not top_scores:
                return ""
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            cat_names = [name.replace('_', ' ').title() for name, _ in top_scores]
            confidences = [score * 100 for _, score in top_scores]
            
            bars = ax.bar(range(len(cat_names)), confidences, color='#4D96FF', alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=10, weight='bold')
            
            ax.set_xticks(range(len(cat_names)))
            ax.set_xticklabels(cat_names, rotation=45, ha='right')
            ax.set_ylabel('신뢰도 (%)', fontsize=11, rotation=0, labelpad=35)
            ax.set_title('사이트 카테고리 분류 신뢰도', fontsize=12, weight='bold', pad=15)
            ax.set_ylim(0, 110)
            ax.grid(axis='y', alpha=0.3)
            
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            return image_base64
        
        except Exception as e:
            logger.error(f"카테고리 신뢰도 차트 생성 오류: {str(e)}")
            return ""
    
    def _generate_html(self, domain: str, analysis_result: Dict, trust_analysis: Dict,
                      coda_result: Dict, charts: Dict, llm_result: Dict = None) -> str:
        """HTML 보고서 생성"""

        accessibility = analysis_result.get('accessibility', {})
        indexing = analysis_result.get('indexing', {})

        trust_level = trust_analysis.get('trust_level', 'unknown')
        trust_level_ko = {
            'HIGHLY_TRUSTWORTHY': '매우 높음',
            'TRUSTWORTHY': '높음',
            'SUSPICIOUS': '중간 (의심)',
            'UNTRUSTED': '낮음 (위험)',
            'UNREACHABLE': '분석 불가'
        }.get(trust_level, '알 수 없음')

        accessible_badge = '<span class="status-badge status-success">접근 가능</span>' if accessibility.get('is_accessible') else '<span class="status-badge status-danger">접근 불가</span>'
        ahmia_badge = '<span class="status-badge status-success">검색됨</span>' if indexing.get('ahmia_found') else '<span class="status-badge status-danger">미발견</span>'
        ddgo_badge = '<span class="status-badge status-success">검색됨</span>' if indexing.get('duckduckgo_found') else '<span class="status-badge status-danger">미발견</span>'

        trust_chart = ''
        if charts.get('trust_radar'):
            trust_chart = '<div class="section"><div class="section-title">신뢰도 그래프</div><div class="chart-container"><img src="data:image/png;base64,' + charts['trust_radar'] + '" alt="신뢰도"></div></div>'
        
        now = datetime.now()
        timestamp = now.strftime('%Y년 %m월 %d일 %H:%M:%S')
        timestamp_footer = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # HTML 조립
        html = ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                '<title>분석 보고서 - ' + domain + '</title>')
        
        # CSS 스타일
        css = ('<style>'
               '* { margin: 0; padding: 0; box-sizing: border-box; }'
               'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.6; color: #333; padding: 20px; }'
               '.container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); }'
               '.header { background: linear-gradient(135deg, rgb(102, 126, 234) 0%, rgb(118, 75, 162) 100%); color: white; padding: 40px; text-align: center; }'
               '.header h1 { font-size: 32px; margin-bottom: 10px; word-break: break-all; }'
               '.header p { font-size: 14px; opacity: 0.9; }'
               '.content { padding: 40px; }'
               '.section { margin-bottom: 40px; }'
               '.section-title { font-size: 20px; font-weight: bold; color: #667eea; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }'
               '.trust-card { background: linear-gradient(135deg, rgb(102, 126, 234) 0%, rgb(118, 75, 162) 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }'
               '.trust-score { font-size: 48px; font-weight: bold; margin: 20px 0; }'
               '.trust-level { font-size: 18px; opacity: 0.9; }'
               '.score-breakdown { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 20px; }'
               '.score-item { background: white; padding: 15px; border-radius: 8px; text-align: center; }'
               '.score-item-value { font-size: 24px; font-weight: bold; color: #667eea; }'
               '.score-item-label { font-size: 12px; color: #666; margin-top: 5px; }'
               '.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px; }'
               '.info-box { background: #f5f7fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; margin-top: 10px; }'
               '.info-box-title { font-weight: bold; color: #667eea; margin-bottom: 8px; font-size: 12px; }'
               '.info-box-content { font-size: 14px; color: #333; }'
               '.status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; margin-right: 8px; }'
               '.status-success { background: #d4edda; color: #155724; }'
               '.status-danger { background: #f8d7da; color: #721c24; }'
               '.chart-container { text-align: center; margin: 20px 0; }'
               '.chart-container img { max-width: 100%; height: auto; border-radius: 8px; }'
               '.analysis-section { background: #f5f7fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }'
               '.analysis-text { white-space: pre-wrap; font-family: monospace; font-size: 13px; line-height: 1.8; }'
               '.footer { background: #f5f7fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; }'
               'table { width: 100%; border-collapse: collapse; margin-top: 10px; }'
               'th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }'
               'th { background: #f5f7fa; font-weight: bold; color: #667eea; }'
               'tr:hover { background: #f9f9f9; }'
               '</style></head><body>')
        
        html += css
        
        # 헤더
        html += '<div class="container"><div class="header"><h1>도메인 분석 보고서</h1><p>대상: <strong>' + domain + '</strong></p><p>생성: ' + timestamp + '</p></div>'
        
        # 콘텐츠
        html += '<div class="content">'
        
        # 경고 메시지가 있으면 먼저 표시
        if analysis_result.get('analysis_warning'):
            html += '<div class="section" style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin-bottom: 20px;"><div style="color: #856404; font-weight: bold;">⚠️ 분석 제한 사항</div><div style="color: #856404; margin-top: 10px;">' + analysis_result['analysis_warning'] + '</div></div>'
        
        # 신뢰도 섹션
        html += '<div class="section"><div class="section-title">종합 신뢰도 분석</div>'
        html += '<div class="trust-card"><div>신뢰도 점수</div>'
        html += '<div class="trust-score">' + str(trust_analysis['total_score']) + '/100</div>'
        html += '<div class="trust-level">' + trust_level_ko + '</div></div>'
        html += '<div class="score-breakdown">'
        html += '<div class="score-item"><div class="score-item-value">' + str(trust_analysis['score_breakdown']['accessibility']['score']) + '</div><div class="score-item-label">접근성 (40점)</div></div>'
        html += '<div class="score-item"><div class="score-item-value">' + str(trust_analysis['score_breakdown']['indexing']['score']) + '</div><div class="score-item-label">색인 (30점)</div></div>'
        html += '<div class="score-item"><div class="score-item-value">' + str(trust_analysis['score_breakdown']['content']['score']) + '</div><div class="score-item-label">콘텐츠 (30점)</div></div>'
        html += '</div></div>'
        
        # 상세 분석
        html += '<div class="section"><div class="section-title">상세 분석</div>'
        html += '<div class="analysis-section"><div class="analysis-text">' + trust_analysis['detailed_analysis'] + '</div></div></div>'
        
        # 접근성
        html += '<div class="section"><div class="section-title">접근성 정보</div>'
        
        # HTML 수집 상태 표시
        html_collected = analysis_result.get('html_collected', False)
        html_collected_badge = '<span class="status-badge status-success">수집됨</span>' if html_collected else '<span class="status-badge status-danger">미수집</span>'
        html += '<div class="info-grid"><div class="info-box"><div class="info-box-title">HTML 수집</div><div class="info-box-content">' + html_collected_badge + '</div></div>'
        
        html += '<div class="info-box"><div class="info-box-title">HTTP 상태</div><div class="info-box-content">' + str(accessibility.get('status_code', 'N/A')) + ' ' + accessible_badge + '</div></div>'
        response_time = accessibility.get('response_time') or 0
        html += '<div class="info-box"><div class="info-box-title">응답 시간</div><div class="info-box-content">' + str(round(response_time, 2)) + '초</div></div>'
        html += '</div>'
        
        # Fallback 정보가 있으면 추가
        if accessibility.get('fallback_domain'):
            fallback_status = '<span class="status-badge status-success">재확인 성공</span>' if accessibility.get('fallback_accessible') else '<span class="status-badge status-danger">재확인 실패</span>'
            html += '<div class="info-box" style="margin-top: 10px;"><div class="info-box-title">재검증 정보</div><div class="info-box-content">도메인: ' + accessibility['fallback_domain'] + '<br>상태: ' + fallback_status + '</div></div>'
        
        html += '</div>'
        
        # 검색 색인
        html += '<div class="section"><div class="section-title">검색 색인 정보</div>'
        html += '<table><tr><th>엔진</th><th>상태</th><th>결과</th></tr>'
        html += '<tr><td>Ahmia</td><td>' + ahmia_badge + '</td><td>' + str(indexing.get('ahmia_results', '0')) + '건</td></tr>'
        
        # DuckDuckGo 결과를 True/False로 표시
        ddgo_result_text = 'True' if indexing.get('duckduckgo_found') else 'False'
        html += '<tr><td>DuckDuckGo</td><td>' + ddgo_badge + '</td><td>' + ddgo_result_text + '</td></tr>'
        html += '</table>'
        
        # 접근 가능한 도메인의 상대 경로
        extracted_urls = indexing.get('extracted_urls', [])
        if extracted_urls and len(extracted_urls) > 0:
            # 최대 15개까지만 표시
            display_urls = extracted_urls[:15]
            urls_html = '<br>'.join(display_urls)
            html += '<div class="info-box" style="margin-top: 10px;"><div class="info-box-title">접근 가능한 도메인의 상대경로 (' + str(len(extracted_urls)) + '개)</div><div class="info-box-content" style="word-break: break-all; font-size: 12px; max-height: 300px; overflow-y: auto;">' + urls_html + '</div></div>'
        
        # HTML 콘텐츠에서 추출된 어니언 도메인 (HTML 수집된 경우만)
        if html_collected:
            html_content = analysis_result.get('html_content', '')
            extracted_domains = self._extract_onion_domains(html_content)
            
            if extracted_domains:
                domains_html = '<br>'.join(extracted_domains[:10])  # 최대 10개 표시
                html += '<div class="info-box" style="margin-top: 10px;"><div class="info-box-title">페이지 내 어니언 도메인 (' + str(len(extracted_domains)) + '개)</div><div class="info-box-content">' + domains_html + '</div></div>'
        
        html += '</div>'
        
        # CoDA 범죄 카테고리 (학습된 분류기)
        html += '<div class="section"><div class="section-title">🎯 CoDA 범죄 카테고리</div>'
        if not html_collected:
            html += '<div class="info-box" style="background:#e7e8ea;"><div class="info-box-content">HTML 미수집으로 인해 분석을 수행하지 않았습니다.</div></div>'
        elif not coda_result.get('available'):
            html += '<div class="info-box" style="background:#fff3cd;"><div class="info-box-content">⚠️ 학습된 모델 없음 — <code>python3 analyzers/train_coda_classifier.py</code> 실행 필요</div></div>'
        else:
            cat = coda_result.get('category', 'unknown').upper()
            conf = round(coda_result.get('confidence', 0) * 100, 1)
            uncertain = coda_result.get('uncertain', False)
            badge_style = 'background:#fff3cd; border-left-color:#856404;' if uncertain else ''
            uncertain_note = ' &nbsp;<span style="color:#856404; font-size:12px;">⚠️ 분류 불확실 (1·2위 차이 10% 미만)</span>' if uncertain else ''
            html += (
                '<div class="info-box" style="' + badge_style + '">'
                '<div class="info-box-title">분류 결과</div>'
                '<div class="info-box-content"><strong style="font-size:18px;">' + cat + '</strong>'
                ' (' + str(conf) + '%)' + uncertain_note + '</div></div>'
            )
            all_probs = coda_result.get('all_probs', {})
            if all_probs:
                probs_html = ' &nbsp;|&nbsp; '.join(
                    f'<b>{k.upper()}</b>: {round(v*100,1)}%'
                    for k, v in list(all_probs.items())[:5]
                )
                html += (
                    '<div class="info-box" style="margin-top:8px;">'
                    '<div class="info-box-title">상위 5개 확률</div>'
                    '<div class="info-box-content" style="font-size:13px;">' + probs_html + '</div></div>'
                )
        html += '</div>'
        
        # 차트
        html += trust_chart

        # LLM 사이트 요약 섹션
        if llm_result and llm_result.get('success'):
            risk_colors = {
                '낮음': '#d4edda', '중간': '#fff3cd',
                '높음': '#f8d7da', '매우높음': '#f8d7da'
            }
            risk_text_colors = {
                '낮음': '#155724', '중간': '#856404',
                '높음': '#721c24', '매우높음': '#721c24'
            }
            risk = llm_result.get('risk_level', '')
            risk_bg = risk_colors.get(risk, '#f5f7fa')
            risk_tc = risk_text_colors.get(risk, '#333')

            features_html = ''
            features = llm_result.get('notable_features', [])
            if features:
                features_html = '<ul style="margin: 8px 0 0 16px;">' + ''.join(
                    f'<li style="font-size:13px; margin-bottom:4px;">{f}</li>' for f in features
                ) + '</ul>'

            html += (
                '<div class="section">'
                '<div class="section-title">🤖 AI 사이트 분석 (Claude)</div>'
                '<div class="analysis-section">'
                '<div class="info-grid">'
                '<div class="info-box"><div class="info-box-title">사이트 유형</div>'
                '<div class="info-box-content">' + (llm_result.get('site_type') or '-') + '</div></div>'
                '<div class="info-box"><div class="info-box-title">주요 언어</div>'
                '<div class="info-box-content">' + (llm_result.get('language') or '-') + '</div></div>'
                '</div>'
                '<div class="info-box" style="margin-top:10px;"><div class="info-box-title">목적</div>'
                '<div class="info-box-content">' + (llm_result.get('purpose') or '-') + '</div></div>'
                '<div class="info-box" style="margin-top:10px;"><div class="info-box-title">요약</div>'
                '<div class="info-box-content">' + (llm_result.get('summary') or '-') + '</div></div>'
                '<div class="info-box" style="margin-top:10px; background:' + risk_bg + '; border-left-color:' + risk_tc + ';">'
                '<div class="info-box-title" style="color:' + risk_tc + ';">AI 위험도 평가</div>'
                '<div class="info-box-content" style="color:' + risk_tc + ';">'
                '<strong>' + risk + '</strong> — ' + (llm_result.get('risk_reason') or '') +
                '</div></div>'
                + (('<div class="info-box" style="margin-top:10px;"><div class="info-box-title">주목할 특징</div>'
                    '<div class="info-box-content">' + features_html + '</div></div>') if features_html else '')
                + '<div style="font-size:11px; color:#999; margin-top:8px;">분석 모델: ' + (llm_result.get('model_used') or '') + '</div>'
                '</div></div>'
            )
        elif llm_result and not llm_result.get('success'):
            error_msg = llm_result.get('error', '')
            if error_msg not in ('HTML 미수집', 'API 키 미설정'):
                html += (
                    '<div class="section"><div class="section-title">🤖 AI 사이트 분석 (Claude)</div>'
                    '<div class="info-box" style="background:#e7e8ea;"><div class="info-box-content">'
                    'AI 분석 실패: ' + error_msg + '</div></div></div>'
                )

        # 조사 결론
        html += '<div class="section"><div class="section-title">조사 결론</div>'
        html += '<div class="analysis-section"><p><strong>도메인:</strong> ' + domain + '</p>'
        html += '<p><strong>신뢰도:</strong> ' + trust_level_ko + ' (' + str(trust_analysis['total_score']) + '/100)</p>'
        html += '<p><strong>접근성:</strong> ' + ('가능' if accessibility.get('is_accessible') else '불가') + '</p>'
        
        # HTML 수집 상태 표시
        if html_collected:
            html += '<p><strong>HTML 수집:</strong> <span style="color: green;">✓ 수집됨</span></p>'
        else:
            html += '<p><strong>HTML 수집:</strong> <span style="color: red;">✗ 미수집</span></p>'
            html += '<p><strong>분석 제한:</strong> 도메인에 접근할 수 없어 카테고리 분류 및 불법 콘텐츠 분석을 수행하지 않았습니다.</p>'
        
        html += '<p><strong>색인 상태:</strong> ' + ('공개' if indexing.get('combined_found') else '은닉') + '</p>'
        if coda_result and coda_result.get('available'):
            uncertain_txt = ' (불확실)' if coda_result.get('uncertain') else ''
            html += '<p><strong>CoDA 범죄 카테고리:</strong> ' + coda_result.get('category', 'unknown').upper() + uncertain_txt + '</p>'
        html += '</div></div>'
        
        # 푸터
        html += '</div><div class="footer"><p>자동 생성 | ' + timestamp_footer + '</p></div></div></body></html>'
        
        return html
