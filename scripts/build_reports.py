#!/usr/bin/env python3
import csv, json, html, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "research" / "logic-market-headmap-2026"

def rows(path):
    with path.open(newline="") as f: return list(csv.DictReader(f))

def esc(v): return html.escape(str(v or ""))
def num(v):
    try: return int(float(v))
    except: return 0

def mini_bar(value, maximum, color="var(--accent)"):
    width = 0 if not maximum else max(2, round(value / maximum * 100, 1))
    return f'<span class="bar"><i style="width:{width}%;background:{color}"></i></span>'

INTERACTIVE_JS = """
<script>
// Active nav highlight on scroll
const secs=document.querySelectorAll('section[id]'),navLinks=document.querySelectorAll('nav a');
const obs=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){navLinks.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+e.target.id))}})},{rootMargin:'-20% 0px -75% 0px'});
secs.forEach(s=>obs.observe(s));
// Search filter for quotes and table rows
document.querySelectorAll('.quote-search').forEach(input=>{
  input.addEventListener('input',()=>{const q=input.value.toLowerCase();const container=input.closest('section')||input.parentElement;
  container.querySelectorAll('.quote[data-cat]').forEach(el=>{el.classList.toggle('hidden',q&&!el.textContent.toLowerCase().includes(q))});
  container.querySelectorAll('tr.filterable').forEach(el=>{el.classList.toggle('hidden',q&&!el.textContent.toLowerCase().includes(q))});});
});
// Category chip filters
document.querySelectorAll('.cat-chip').forEach(chip=>{
  chip.addEventListener('click',()=>{
    const container=chip.closest('section')||chip.parentElement;
    chip.classList.toggle('on');
    const activeChips=[...container.querySelectorAll('.cat-chip.on')].map(c=>c.dataset.cat);
    container.querySelectorAll('.quote[data-cat]').forEach(el=>{
      el.classList.toggle('hidden',activeChips.length>0&&!activeChips.includes(el.dataset.cat));
    });
    container.querySelectorAll('tr.filterable').forEach(el=>{
      el.classList.toggle('hidden',activeChips.length>0&&!activeChips.some(c=>el.textContent.toLowerCase().includes(c.toLowerCase())));
    });
  });
});
// Sortable table headers
document.querySelectorAll('.sort-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const th=btn.closest('th'),table=th.closest('table'),tbody=table.querySelector('tbody');
    const idx=[...th.parentElement.children].indexOf(th);
    const rowsArr=[...tbody.querySelectorAll('tr')];
    const dir=th.dataset.dir==='asc'?'desc':'asc'; th.dataset.dir=dir;
    rowsArr.sort((a,b)=>{
      let av=a.children[idx]?.textContent.trim().replace(/[,%#]/g,''),bv=b.children[idx]?.textContent.trim().replace(/[,%#]/g,'');
      const an=parseFloat(av.replace(/,/g,'')),bn=parseFloat(bv.replace(/,/g,''));
      if(!isNaN(an)&&!isNaN(bn))return dir==='asc'?an-bn:bn-an;
      return dir==='asc'?av.localeCompare(bv):bv.localeCompare(av);
    });
    rowsArr.forEach(r=>tbody.appendChild(r));
  });
});
</script>
"""

def shell(arm, subtitle, stats, sections, downloads, theme):
    nav = ''.join(f'<a href="#{sid}">{label}</a>' for sid,label in [
        ('overview','Overview'),('categories','Categories'),('topics','Topics'),('trends','Trends'),('roles','Voices'),
        ('connections','Connections'),('evidence','Evidence'),('implications','Implications'),
        ('priorities','Content priorities'),('method','Method'),('downloads','Downloads')])
    stat_html=''.join(f'<div class="metric"><strong>{esc(v)}</strong><span>{esc(k)}</span></div>' for k,v in stats)
    dl=''.join(f'<a class="download" href="{esc(url)}" download><span>{esc(label)}</span><small>{esc(note)}</small></a>' for label,url,note in downloads)
    css_interactive = '.filter-bar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.filter-bar input{flex:1;min-width:200px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;font:14px Manrope;background:var(--panel);color:var(--ink)}.filter-bar input:focus{outline:2px solid var(--accent);border-color:var(--accent)}.cat-chip{font:500 11px DM Mono;padding:6px 10px;border-radius:99px;cursor:pointer;border:1px solid var(--line);background:var(--panel);transition:.15s}.cat-chip:hover,.cat-chip.on{background:var(--accent);color:var(--hero);border-color:var(--accent)}.quote[data-cat]{transition:opacity .15s}.quote.hidden{display:none}tr.filterable.hidden{display:none}.sort-btn{cursor:pointer;user-select:none}.sort-btn:after{content:" \\2195";opacity:.4}nav a.active{background:var(--accent);color:var(--hero)}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(arm)} Market Heatmap</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{{--ink:{theme['ink']};--paper:{theme['paper']};--panel:{theme['panel']};--muted:{theme['muted']};--accent:{theme['accent']};--accent2:{theme['accent2']};--line:{theme['line']};--hero:{theme['hero']}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.65 Manrope,sans-serif}}a{{color:inherit}}header{{background:var(--hero);color:white;padding:64px max(24px,calc((100% - 1180px)/2)) 42px;position:relative;overflow:hidden}}header:after{{content:'';position:absolute;right:-120px;top:-160px;width:480px;height:480px;border:1px solid color-mix(in srgb,var(--accent) 55%,transparent);border-radius:50%;box-shadow:0 0 0 55px color-mix(in srgb,var(--accent) 7%,transparent),0 0 0 110px color-mix(in srgb,var(--accent) 5%,transparent)}}.eyebrow{{font:500 12px DM Mono;letter-spacing:.15em;color:var(--accent)}}h1{{font-size:clamp(38px,6vw,72px);line-height:.98;letter-spacing:-.055em;margin:18px 0;max-width:820px}}header p{{max-width:750px;color:#c9d1df;font-size:17px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#ffffff25;margin-top:38px;position:relative;z-index:1}}.metric{{background:#ffffff0b;padding:20px}}.metric strong{{display:block;font-size:25px;color:var(--accent)}}.metric span{{font:11px DM Mono;text-transform:uppercase;letter-spacing:.08em;color:#d7dce6}}nav{{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--paper) 92%,transparent);backdrop-filter:blur(15px);border-bottom:1px solid var(--line);display:flex;gap:4px;overflow:auto;padding:10px max(16px,calc((100% - 1180px)/2))}}nav a{{padding:8px 11px;text-decoration:none;font:500 11px DM Mono;text-transform:uppercase;white-space:nowrap;border-radius:99px}}nav a:hover{{background:var(--accent);color:var(--hero)}}main{{max-width:1180px;margin:auto;padding:30px 24px 90px}}section{{padding:46px 0;border-bottom:1px solid var(--line)}}.section-kicker{{font:500 11px DM Mono;color:var(--accent2);text-transform:uppercase;letter-spacing:.12em}}h2{{font-size:32px;letter-spacing:-.035em;margin:7px 0 22px}}h3{{font-size:18px;margin:24px 0 10px}}.lead{{font-size:18px;max-width:850px;color:var(--muted)}}.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.card{{background:var(--panel);border:1px solid var(--line);padding:22px;border-radius:12px}}.callout{{border-left:4px solid var(--accent);background:color-mix(in srgb,var(--accent) 10%,var(--panel));padding:18px 20px;margin:18px 0}}table{{width:100%;border-collapse:collapse;background:var(--panel);font-size:13px}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{font:500 10px DM Mono;text-transform:uppercase;color:var(--muted);position:sticky;top:48px;background:var(--panel)}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:620px}}.bar{{width:110px;height:7px;background:var(--line);display:inline-block;border-radius:8px;overflow:hidden}}.bar i{{height:100%;display:block;border-radius:8px}}.heat td:not(:first-child){{text-align:center;font-family:DM Mono}}.quote{{padding:18px 0;border-bottom:1px solid var(--line)}}.quote blockquote{{margin:0 0 9px;font-size:17px;line-height:1.5}}.quote small{{font:11px DM Mono;color:var(--muted)}}details{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:9px 0}}summary{{cursor:pointer;font-weight:700}}.chips{{display:flex;flex-wrap:wrap;gap:8px}}.chip{{font:11px DM Mono;border:1px solid var(--line);padding:7px 9px;border-radius:99px}}.downloads{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.download{{display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;text-decoration:none}}.download:hover{{border-color:var(--accent);transform:translateY(-2px)}}.download small{{color:var(--muted)}}footer{{padding:24px;text-align:center;font:11px DM Mono;color:var(--muted)}}@media(max-width:760px){{.metrics,.grid2,.downloads{{grid-template-columns:1fr 1fr}}h1{{font-size:44px}}th{{position:static}}}}@media(max-width:480px){{.metrics,.grid2,.downloads{{grid-template-columns:1fr}}}}
{css_interactive}
</style></head><body><header><span class="eyebrow">{esc(arm.upper())}</span><h1>Market Heatmap</h1><p>{esc(subtitle)}</p><div class="metrics">{stat_html}</div></header><nav>{nav}</nav><main>{''.join(sections)}<section id="downloads"><span class="section-kicker">Resources</span><h2>Download the evidence</h2><div class="downloads">{dl}</div></section></main><footer>Logic Inc · External-market research · Counts are corpus signals, not market-size estimates.</footer>
{INTERACTIVE_JS}</body></html>'''

def section(sid,kicker,title,body): return f'<section id="{sid}"><span class="section-kicker">{kicker}</span><h2>{title}</h2>{body}</section>'

def category_expansion(arm):
    data=rows(ROOT/'category-source-inventory.csv')
    src_cats=sorted(set(r['category'] for r in data))
    src_chips=''.join(f'<span class="cat-chip" data-cat="{esc(c)}">{esc(c)}</span>' for c in src_cats)
    table=''.join(f'<tr class="filterable"><td><b>{esc(r["category"])}</b></td><td><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["source"])}</a><br><small>{esc(r["format"])} &middot; {esc(r["date"])}</small></td><td>{esc(r["evidence_depth"])}</td><td>{esc(r["primary_signals"])}</td></tr>' for r in data)
    if arm=='agency':
        intro='This supplemental pass expands Agency evidence into beauty operations, electronics hardware, and wine/spirits. It strengthens the manufacturing, sourcing, quality, packaging engineering, freight, compliance, and launch-control layers without mixing unclassified sources into the legacy counts.'
        cards='<div class="grid2"><div class="card"><h3>Beauty + luxury goods</h3><p>Compatibility, dispensing, supplier quality, refill systems, luxury presentation, launch timing, and repeat-order economics connect packaging to ongoing operations.</p><h3>Consumer electronics + babytech</h3><p>Protective engineering, testing, cube, global sourcing, damage, setup, retailer display, safety, and returns make these high-fit Agency categories.</p></div><div class="card"><h3>Wine, spirits + jewelry</h3><p>Bottle weight, closures, decoration, theft risk, fulfillment, line performance, compliance, and retailer mandates turn presentation into a supply-chain system.</p><h3>Scaling elevated brands</h3><p>The shared pattern is earlier decisions, validated specifications, design-for-manufacture, inventory visibility, and one owner across suppliers and channels.</p></div></div>'
    else:
        intro='This supplemental pass adds category-native packaging evidence beyond the food/beverage-heavy Startup CPG reference. It covers beauty, electronics, wine/spirits, and packaging-specialist podcasts while preserving the boundary between the original quantitative base and newly screened sources.'
        cards='<div class="grid2"><div class="card"><h3>Beauty + influencer kits</h3><p>Formula compatibility, refill formats, tactile design, creator-ready reveals, personalized inserts, kitting, protection, and the realities of producing low-volume campaign packaging.</p><h3>Electronics + babytech</h3><p>Paper retention structures, protection, safety cues, setup hierarchy, theft/display needs, premium unboxing, cube reduction, and ecommerce versus retail formats.</p></div><div class="card"><h3>Luxury, jewelry, wine + spirits</h3><p>Perceived value, gifting, closures, layered reveals, theft risk, lightweighting, premium cues, retailer mandates, and the economics of first-order versus repeat-order packaging.</p><h3>Packaging execution</h3><p>Specification management, sampling, transition governance, testing, automation, lifecycle assessment, claims, and design-for-manufacture.</p></div></div>'
    return section('categories','02 &middot; Category expansion','Beyond the food/beverage bias',f'<p class="lead">{intro}</p>{cards}<details open><summary>Open the {len(data)}-source expansion inventory</summary><div class="filter-bar"><input class="quote-search" placeholder="Filter sources by category, name, or signal&hellip;"><div>{src_chips}</div></div><div class="scroll"><table><thead><tr><th>Category</th><th>Source</th><th>Depth</th><th>Primary signals</th></tr></thead><tbody>{table}</tbody></table></div></details><div class="callout"><b>Counting rule:</b> these sources remain a separately attributable layer until full-text normalization, deduplication, and classification are complete.</div>')

def verified_podcast_quotes(arm):
    data=[r for r in rows(ROOT/'verified-podcast-quotes.csv') if r['arm'].lower()==arm.lower()]
    cats=sorted(set(r['category'] for r in data))
    chips=''.join(f'<span class="cat-chip" data-cat="{esc(c)}">{esc(c)}</span>' for c in cats)
    cards=''.join(f'<div class="quote" data-cat="{esc(r["category"])}"><blockquote>&ldquo;{esc(r["quote"])}&rdquo;</blockquote><small><b>{esc(r["speaker"])}</b> &middot; {esc(r["job_title"])} &middot; {esc(r["company"])}<br>{esc(r["podcast"])} &middot; <a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["episode"])}</a><br><span class="chip">{esc(r["category"])}</span> &middot; {esc(r["verification_status"])}</small></div>' for r in data)
    return f'<h3>Verified podcast quotes</h3><p class="lead">Only quotations with a confirmed speaker, company, job title, podcast, episode title, and direct episode link appear here.</p><div class="filter-bar"><input class="quote-search" placeholder="Search quotes by keyword, speaker, company, or topic&hellip;"><div>{chips}</div></div>'+cards

def painpoint_insights(arm):
    data=[r for r in rows(ROOT/'outreach-painpoint-insights.csv') if r['arm'].lower()==arm.lower()]
    body=''.join(f'<tr><td><b>{esc(r["painpoint"])}</b></td><td>{esc(r["outreach_one_liner"])}</td><td>{esc(r["guide_or_blog_angle"])}</td></tr>' for r in data)
    return '<h3>Outreach one-liners and content pain points</h3><p class="lead">Editorial paraphrases distilled from unverified excerpts. Use as messaging hypotheses, not attributed quotations.</p><div class="scroll"><table><thead><tr><th>Pain point</th><th>Outreach one-liner</th><th>Guide or blog angle</th></tr></thead><tbody>'+body+'</tbody></table></div>'

def content_priorities(arm):
    data=[r for r in rows(ROOT/'content-priorities.csv') if r['arm'].lower()==arm.lower()]
    briefs={(r['arm'].lower(),r['rank']):r for r in rows(ROOT/'content-priority-briefs.csv')}
    body=''.join(f'<tr><td><b>#{esc(r["rank"])}</b></td><td><b>{esc(r["topic"])}</b><br><small>{esc(r["recommended_format"])}</small></td><td>{esc(r["score"])}</td><td>{esc(r["primary_evidence"])}</td><td>{esc(r["content_gap"])}</td><td>{esc(r["commercial_role"])}</td></tr>' for r in data)
    detail=''
    for r in data:
        key = (arm.lower(), r['rank'])
        b = briefs.get(key)
        if not b: continue
        detail += f'<details><summary><span class="chip">#{esc(r["rank"])}</span> {esc(r["topic"])} &middot; {esc(r["score"])} points</summary><div class="grid2"><div><h3>ICP and buying moment</h3><p><b>Audience:</b> {esc(b["target_icp"])}</p><p><b>Trigger:</b> {esc(b["buying_trigger"])}</p><p><b>Core thesis:</b> {esc(b["core_thesis"])}</p><h3>Required elements</h3><p>{esc(b["key_elements"])}</p></div><div><h3>Evidence and persuasion</h3><p><b>Proof to include:</b> {esc(b["proof_to_include"])}</p><p><b>Objections to address:</b> {esc(b["objections_to_address"])}</p><p><b>Soft CTA:</b> {esc(b["soft_cta"])}</p></div></div></details>'
    return section('priorities','08 &middot; Content priorities','What Logic should publish next','<p class="lead">Ten research-ranked priorities for this arm. The table explains why each topic matters; the briefs below define what each piece must contain for Logic\'s target ICP.</p><div class="scroll"><table><thead><tr><th>Rank</th><th>Topic / format</th><th><span class="sort-btn">Score</span></th><th>Evidence</th><th>Current gap</th><th>Commercial role</th></tr></thead><tbody>'+body+'</tbody></table></div><h3>Detailed content briefs</h3>'+detail+'<div class="callout"><b>Use rule:</b> validate claims against current services, authorized client evidence, and live search demand before production. Direct founder quotes require complete attribution.</div>')

def agency():
    base=SRC/'agency'; dist=rows(base/'agency-topic-distribution.csv'); trends=rows(base/'agency-topic-trends.csv'); roles=rows(base/'agency-role-analysis.csv'); co=rows(base/'agency-topic-cooccurrence.csv'); claims=rows(base/'agency-claims-and-quotes.csv')
    maxm=max(num(x['total_mentions']) for x in dist); years=[k for k in trends[0] if re.match(r'20\d\dQ\d',k)]
    dist_table=''.join(f"<tr><td>{i}</td><td><b>{esc(r['topic'])}</b><br><small>{esc(r['agency_parent_theme'])}</small></td><td>{num(r['total_mentions']):,}</td><td>{r['share_pct']}%</td><td>{mini_bar(num(r['total_mentions']),maxm)}</td></tr>" for i,r in enumerate(dist,1))
    heat=''.join('<tr><td><b>'+esc(r['topic'])+'</b></td>'+''.join(f'<td style="background:color-mix(in srgb,var(--accent) {min(80,num(r[y])/5)}%,var(--panel))">{num(r[y])}</td>' for y in years)+'</tr>' for r in trends)
    role_rows=''.join(f"<tr><td>{esc(r['topic'])}</td><td>{num(r['host_mentions']):,}</td><td>{num(r['guest_mentions']):,}</td><td>{r['guest_share_pct']}%</td></tr>" for r in roles)
    co_rows=''.join(f"<tr><td>{esc(r['topic_a'])}</td><td>{esc(r['topic_b'])}</td><td>{num(r['co_occurrences']):,}</td></tr>" for r in co[:35])
    quote_html=''.join(f'<div class="quote"><blockquote>&ldquo;{esc(r["sentence"])}&rdquo;</blockquote><small>{esc(r["speaker"])} &middot; {esc(r["source_title"])} &middot; {esc(r["topic"])}</small></div>' for r in claims[:45])
    sections=[
      section('overview','01 &middot; Market signal','What the Agency evidence says','<p class="lead">Retail success dominates the conversation, but the operational substrate is the strategic opening: co-manufacturing, supplier control, demand planning, unit economics, packaging compliance, and the systems required to scale without adding chaos.</p><div class="grid2"><div class="card"><h3>Commercial territory</h3><p>Own the gap between winning distribution and operating it profitably. The strongest Logic-specific angle is not &ldquo;retail consulting&rdquo;; it is execution across suppliers, inventory, compliance, cost, and channel complexity.</p></div><div class="card"><h3>Buyer language</h3><p>Use concrete operating language: <b>ops nightmare, co-man, bottoms-up forecast, working-capital problem, get back in their queue</b>. Avoid abstract consulting vocabulary.</p></div></div><div class="callout"><b>Interpretation rule:</b> frequency reflects this corpus, not addressable market size. Retail-heavy source composition is a known constraint.</div>'),
      category_expansion('agency'),
      section('topics','02 &middot; Topic distribution','Where attention concentrates',f'<div class="scroll"><table><thead><tr><th>#</th><th>Topic</th><th><span class="sort-btn">Mentions</span></th><th><span class="sort-btn">Share</span></th><th>Relative volume</th></tr></thead><tbody>{dist_table}</tbody></table></div>'),
      section('trends','03 &middot; Time series','Topic heatmap by quarter',f'<p class="lead">Directional shifts across the collected episodes. The final quarter may be partial.</p><div class="scroll"><table class="heat"><thead><tr><th>Topic</th>{"".join(f"<th>{y}</th>" for y in years)}</tr></thead><tbody>{heat}</tbody></table></div>'),
      section('roles','04 &middot; Voice analysis','Who is carrying each signal',f'<p class="lead">Guest/operator speech exceeds host framing across every retained topic. This version corrects the source metadata that previously marked all speakers as guests.</p><div class="scroll"><table><thead><tr><th>Topic</th><th><span class="sort-btn">Host</span></th><th><span class="sort-btn">Guest</span></th><th><span class="sort-btn">Guest share</span></th></tr></thead><tbody>{role_rows}</tbody></table></div>'),
      section('connections','05 &middot; Co-occurrence','Which problems travel together',f'<p class="lead">Co-occurrence reveals problem systems, not isolated keywords. Manufacturing and planning repeatedly connect to retail-readiness outcomes.</p><div class="scroll"><table><thead><tr><th>Topic A</th><th>Topic B</th><th><span class="sort-btn">Shared chunks</span></th></tr></thead><tbody>{co_rows}</tbody></table></div>'),
      section('evidence','06 &middot; Market language','Evidence and pain-language explorer',painpoint_insights('agency')+verified_podcast_quotes('agency')+f'<details><summary>Open 45 unverified research excerpts</summary><p>These legacy excerpts are not approved for public quotation until every attribution field is verified.</p>{quote_html}</details>'),
      section('implications','07 &middot; GTM implications','What Logic Agency can do with this','<div class="grid2"><div class="card"><h3>Positioning</h3><ul><li>Lead with operational ownership, not advisory.</li><li>Connect retail growth to inventory, cash, compliance, and supplier control.</li><li>Differentiate from brokers and software by owning execution across the stack.</li></ul></div><div class="card"><h3>Content priorities</h3><ol><li>Co-manufacturer selection and scale-up</li><li>Demand planning and S&amp;OP</li><li>Gross-margin and landed-cost control</li><li>Retail compliance and EDI</li><li>Hire vs. embedded operations</li></ol></div></div>'),
      content_priorities('agency'),
      section('method','08 &middot; Methodology','How the Agency map was built','<p class="lead">6,854 multi-label classified chunks were filtered from an external Startup CPG corpus across 332 sources. Seventeen Agency-relevant topics were retained. Topic counts can overlap because a chunk can carry multiple labels. Host/guest roles were repaired using known host identities. This is market-language research, not a causal demand model.</p>')]
    dls=[('Content priorities','../content-priorities.csv','Ranked Agency and Pac backlog'),('Verified podcast quotes','../verified-podcast-quotes.csv','Complete attribution required'),('Category expansion','../category-expansion-2026.md','New category findings'),('Source inventory','../category-source-inventory.csv','Screened sources'),('Topic distribution','agency-topic-distribution.csv','17 ranked topics'),('Quarterly trends','agency-topic-trends.csv','13 quarters'),('Co-occurrence','agency-topic-cooccurrence.csv','Problem-system pairs'),('Role analysis','agency-role-analysis.csv','Host vs guest'),('Research excerpts','agency-claims-and-quotes.csv','Unverified excerpts'),('Language map','agency-market-language-map.md','Buyer vocabulary')]
    return shell('Logic Inc · Agency','Supply-chain and operating intelligence for scaling consumer-product brands.',[('External sources','332'),('Classified chunks','6,854'),('Retained topics','17'),('Evidence excerpts','128')],sections,dls,{'ink':'#071126','paper':'#f2f4ef','panel':'#ffffff','muted':'#5d6677','accent':'#dfff00','accent2':'#ff5b22','line':'#dce1d8','hero':'#071126'})

def pac():
    base=SRC/'pac'; dist=rows(base/'pac-topic-distribution.csv'); trends=rows(base/'pac-topic-trends.csv'); roles=rows(base/'pac-role-analysis.csv'); co=rows(base/'pac-topic-cooccurrence.csv'); clean=[json.loads(x) for x in (base/'working/pac-clean-classified.jsonl').read_text().splitlines() if x.strip()]
    maxm=max(num(x['total_mentions']) for x in dist); years=[k for k in trends[0] if re.match(r'20\d\d',k)]
    dist_table=''.join(f"<tr><td>{i}</td><td><b>{esc(r['topic'])}</b><br><small>{esc(r['parent_topic'])}</small></td><td>{num(r['total_mentions'])}</td><td>{r['share_pct']}%</td><td>{mini_bar(num(r['total_mentions']),maxm)}</td></tr>" for i,r in enumerate(dist,1))
    heat=''.join('<tr><td><b>'+esc(r['topic'])+'</b></td>'+''.join(f'<td style="background:color-mix(in srgb,var(--accent) {min(82,num(r[y])*1.6)}%,var(--panel))">{num(r[y])}</td>' for y in years)+'</tr>' for r in trends)
    bytype=Counter(r.get('source_type','unknown') for r in clean); typechips=''.join(f'<span class="chip">{esc(k)} &middot; {v}</span>' for k,v in bytype.most_common())
    co_rows=''.join(f"<tr><td>{esc(r['topic_a'])}</td><td>{esc(r['topic_b'])}</td><td>{num(r['co_occurrences'])}</td></tr>" for r in co)
    excerpts=[]
    for r in clean:
        text=re.sub(r'\s+',' ',r.get('text','')).strip()
        if len(text)>180: excerpts.append((r,text[:560] + ('…' if len(text)>560 else '')))
    quote_html=''.join(f'<div class="quote"><blockquote>&ldquo;{esc(text)}&rdquo;</blockquote><small>{esc(r.get("title"))} &middot; {esc(r.get("source_type"))} &middot; {esc(r.get("date"))}</small></div>' for r,text in excerpts[:35])
    sections=[
      section('overview','01 &middot; Packaging market','What the Pac evidence says','<p class="lead">Packaging performance sits at the intersection of visual identity, conversion, manufacturability, lifecycle impact, and regulatory credibility. The opportunity is not &ldquo;pretty sustainable boxes.&rdquo; It is resolving those tradeoffs from concept through production.</p><div class="grid2"><div class="card"><h3>Strongest intersection</h3><p><b>Design &times; retail fit &times; sustainability.</b> The three most prevalent themes appear in 84&ndash;93 of 103 clean chunks and frequently co-occur.</p></div><div class="card"><h3>Commercial constraint</h3><p>Manufacturing, sourcing, MOQ, cost, and scale determine whether a design can ship. Pac should make this operational layer visible in every design story.</p></div></div><div class="callout"><b>Evidence boundary:</b> the clean source set is beauty-led. Fundraising and non-beauty category coverage remain thin and are shown as gaps.</div>'),
      category_expansion('pac'),
      section('topics','02 &middot; Topic distribution','The packaging conversation',f'<div class="scroll"><table><thead><tr><th>#</th><th>Theme</th><th><span class="sort-btn">Mentions</span></th><th><span class="sort-btn">Share</span></th><th>Relative volume</th></tr></thead><tbody>{dist_table}</tbody></table></div>'),
      section('trends','03 &middot; Time series','Packaging theme heatmap by year',f'<p class="lead">Annual source distribution is uneven, so use this as a coverage view&mdash;not a market-growth forecast.</p><div class="scroll"><table class="heat"><thead><tr><th>Theme</th>{"".join(f"<th>{y}</th>" for y in years)}</tr></thead><tbody>{heat}</tbody></table></div>'),
      section('roles','04 &middot; Source mix','Where the Pac signals come from',f'<p class="lead">Turn-level buyer roles are not consistently available. This report therefore shows source type rather than manufacturing buyer personas it cannot verify.</p><div class="card"><div class="chips">{typechips}</div></div>'),
      section('connections','05 &middot; Co-occurrence','Packaging problems are linked',f'<p class="lead">Design, retail fit, materials, manufacturing, circularity, and claims appear as connected choices&mdash;not separate workstreams.</p><div class="scroll"><table><thead><tr><th>Theme A</th><th>Theme B</th><th><span class="sort-btn">Shared chunks</span></th></tr></thead><tbody>{co_rows}</tbody></table></div>'),
      section('evidence','06 &middot; Source evidence','Packaging evidence explorer',painpoint_insights('pac')+verified_podcast_quotes('pac')+f'<details><summary>Open 35 unverified source excerpts</summary><p>These source-text excerpts are not approved for public quotation until every attribution field is verified.</p>{quote_html}</details>'),
      section('implications','07 &middot; Five decision lenses','What Pac should make visible','<div class="grid2"><div class="card"><h3>Manufacturing</h3><p>Show sourcing, sampling, MOQ, lead time, production risk, quality, and cost&mdash;not only finished photography.</p><h3>Design</h3><p>Demonstrate structural and visual systems, sensory cues, unboxing, and brand coherence.</p><h3>Product categories</h3><p>Build beauty-specific views for skincare, color, haircare, fragrance, wellness, PR kits, and seasonal packaging as evidence grows.</p></div><div class="card"><h3>Retail success</h3><p>Connect packaging to shelf recognition, category cues, premium justification, transit integrity, and conversion.</p><h3>Fundraising</h3><p>Treat packaging as evidence of margin discipline, scalability, compliance readiness, and durable brand equity. Direct investor evidence is still insufficient for frequency claims.</p><h3>Content opportunity</h3><p>Own the tradeoff story: premium without waste, sustainable without greenwashing, distinctive without unmanufacturable complexity.</p></div></div>'),
      content_priorities('pac'),
      section('method','08 &middot; Methodology','How the Pac map was built','<p class="lead">The final thematic base contains 103 clean chunks from 20 external packaging and beauty sources. Nine malformed chunks were excluded. A separate 199-chunk diagnostic combines 103 Pac chunks with 96 rehydrated Startup CPG packaging chunks to test coverage; it is not used to inflate these topic counts. The first combined clustering was rejected because it separated source format rather than topic.</p>')]
    dls=[('Content priorities','../content-priorities.csv','Ranked Agency and Pac backlog'),('Verified podcast quotes','../verified-podcast-quotes.csv','Complete attribution required'),('Category expansion','../category-expansion-2026.md','New category findings'),('Source inventory','../category-source-inventory.csv','Screened sources'),('Topic distribution','pac-topic-distribution.csv','6 reviewed themes'),('Theme trends','pac-topic-trends.csv','Annual coverage'),('Co-occurrence','pac-topic-cooccurrence.csv','15 theme pairs'),('Source roles','pac-role-analysis.csv','Source-type lens'),('Fundraising pass','pac-fundraising-evidence-pass.md','Capital evidence and gaps'),('Taxonomy','pac-corpus-taxonomy.json','Definitions and method')]
    return shell('Logic Pac','Packaging intelligence across design, materials, manufacturing, retail performance, and capital readiness.',[('External sources','20'),('Clean chunks','103'),('Reviewed themes','6'),('Malformed excluded','9')],sections,dls,{'ink':'#251c19','paper':'#f4efe7','panel':'#fffaf2','muted':'#70645d','accent':'#ef6f45','accent2':'#6f7762','line':'#dfd2c5','hero':'#2b211e'})

(ROOT/'agency/agency-heatmap-report.html').write_text(agency())
(ROOT/'pac/pac-heatmap-report.html').write_text(pac())
print('built', (ROOT/'agency/agency-heatmap-report.html').stat().st_size, (ROOT/'pac/pac-heatmap-report.html').stat().st_size)
