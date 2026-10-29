from datetime import datetime, timezone
import pandas as pd
REQUIRED_COLUMNS=['candidate_id','gender_group','qualification_score','skills_score','experience_years','interview_score']
SCORE_COLUMNS=['qualification_score','skills_score','experience_years','interview_score']
def make_sample_data():
 rows=[('C001','Group A',82,88,4,78),('C002','Group A',75,80,3,82),('C003','Group A',90,91,6,85),('C004','Group A',68,72,2,70),('C005','Group A',78,76,5,74),('C006','Group A',85,84,7,80),('C007','Group A',71,73,2,75),('C008','Group A',88,86,8,89),('C009','Group A',64,70,1,68),('C010','Group A',80,83,4,81),('C011','Group B',80,86,4,77),('C012','Group B',74,79,3,80),('C013','Group B',87,90,6,84),('C014','Group B',66,70,2,69),('C015','Group B',76,75,5,72),('C016','Group B',82,83,7,79),('C017','Group B',69,71,2,73),('C018','Group B',86,85,8,87),('C019','Group B',62,68,1,66),('C020','Group B',79,81,4,78)]
 return pd.DataFrame(rows,columns=REQUIRED_COLUMNS)
def validate_candidate_data(df):
 missing=[c for c in REQUIRED_COLUMNS if c not in df.columns]
 if missing:return [f"Missing required columns: {', '.join(missing)}."]
 errors=[]
 if df.empty:errors.append('Dataset is empty.')
 if df.candidate_id.isna().any() or df.candidate_id.astype(str).str.strip().eq('').any():errors.append('candidate_id cannot be blank.')
 if df.candidate_id.duplicated().any():errors.append('candidate_id values must be unique.')
 if df.gender_group.isna().any() or df.gender_group.astype(str).str.strip().eq('').any():errors.append('gender_group cannot be blank.')
 for col in SCORE_COLUMNS:
  n=pd.to_numeric(df[col],errors='coerce')
  if n.isna().any():errors.append(f'{col} must contain numeric values.')
  elif col=='experience_years':
   if (n<0).any():errors.append('experience_years cannot be negative.')
  elif ((n<0)|(n>100)).any():errors.append(f'{col} values must be between 0 and 100.')
 return errors
def score_candidates(df,threshold=70):
 out=df.copy()
 for c in SCORE_COLUMNS:out[c]=pd.to_numeric(out[c],errors='coerce')
 exp=out.experience_years.clip(0,10)*10
 out['baseline_score']=(.30*out.qualification_score+.35*out.skills_score+.15*exp+.20*out.interview_score).round(2)
 out['selected']=out.baseline_score>=threshold
 out['decision']=out.selected.map({True:'SHORTLIST',False:'NOT_SHORTLISTED'})
 return out
def calculate_fairness_metrics(scored,reference_group='Group A'):
 g=scored.groupby('gender_group').agg(candidates=('candidate_id','count'),selected=('selected','sum'),selection_rate=('selected','mean'),mean_score=('baseline_score','mean')).reset_index()
 rates=dict(zip(g.gender_group,g.selection_rate));means=dict(zip(g.gender_group,g.mean_score));rr=rates.get(reference_group,0);rm=means.get(reference_group,0)
 others=[x for x in rates if x!=reference_group]
 if not others:ratio=None;diff=gap=0
 else:
  other=min(others,key=lambda x:rates[x]);orate=rates[other];omean=means[other];ratio=None if rr==0 else round(orate/rr,3);diff=round(abs(rr-orate)*100,2);gap=round(abs(rm-omean),2)
 return {'group_summary':g,'reference_group':reference_group,'selection_rate_difference_pp':diff,'selection_rate_ratio':ratio,'mean_score_gap':gap,'comparison_note':'Compares reference group with the lowest-selection-rate non-reference group.'}
def build_risk_register(scored,metrics):
 risks=[];ratio=metrics['selection_rate_ratio'];diff=metrics['selection_rate_difference_pp']
 if scored.gender_group.nunique()<2: risks.append({'priority':'HIGH','risk':'Insufficient group comparison','evidence':'Only one group is present, so group-level comparisons cannot be made.','recommendation':'Use an authorized, appropriately scoped dataset and document missing data.'})
 else:
  priority='HIGH' if ratio is not None and ratio<.8 else ('MEDIUM' if diff>=10 else 'LOW')
  evidence=f'Selection-rate ratio is {ratio:.2f}, below the 0.80 screening threshold.' if ratio is not None and ratio<.8 else f'Selection-rate difference is {diff:.1f} percentage points; this does not establish absence or presence of bias.'
  risks.append({'priority':priority,'risk':'Potentially unequal selection outcomes','evidence':evidence,'recommendation':'Investigate job relevance, sample size, data quality, subgroup outcomes, and unjustified disparities.'})
 risks += [
 {'priority':'MEDIUM','risk':'Scoring validity and explainability','evidence':'Weights are illustrative and not empirically validated hiring criteria.','recommendation':'Validate criteria through job analysis and document why each factor and weight is appropriate.'},
 {'priority':'MEDIUM','risk':'Privacy and data minimization','evidence':'Candidate data may contain personal information; this prototype lacks production access and retention controls.','recommendation':'Use synthetic or authorized data, minimize identifiers, restrict access, and define retention.'},
 {'priority':'MEDIUM','risk':'Human oversight','evidence':'The tool generates indicators but does not implement a recruiter approval or appeal workflow.','recommendation':'Require qualified human review before consequential decisions and provide a correction or challenge process.'},
 {'priority':'LOW','risk':'Auditability and reproducibility','evidence':'Exports are available, but there is no tamper-evident production audit storage.','recommendation':'Version scoring rules and datasets, store metadata securely, and review changes over time.'}]
 return risks
def build_report(scored,metrics,risks,threshold,reference_group):
 return {'project':'AI RiskLens','assessment_type':'Structured AI hiring risk assessment','generated_at_utc':datetime.now(timezone.utc).isoformat(),'methodology':{'score_formula':'0.30*qualification_score + 0.35*skills_score + 0.15*min(experience_years,10)*10 + 0.20*interview_score','selection_rule':'SHORTLIST if baseline_score >= threshold','threshold':threshold,'reference_group':reference_group,'limitations':['Weights are illustrative, not validated hiring criteria.','Group statistics are descriptive and may be unstable for small samples.','The 0.80 ratio is a screening heuristic, not a legal conclusion.','Results do not establish causal discrimination or guarantee fairness.','The prototype lacks production security and retention controls.']},'summary':{'candidates_assessed':int(len(scored)),'shortlisted':int(scored.selected.sum()),'selection_rate_pct':round(float(scored.selected.mean()*100),2),'threshold':threshold,'reference_group':reference_group,'selection_rate_difference_pp':metrics['selection_rate_difference_pp'],'selection_rate_ratio':metrics['selection_rate_ratio'],'mean_score_gap':metrics['mean_score_gap'],'risk_items':len(risks),'interpretation':'Screening indicators only; not proof of discrimination, fairness, or legal compliance.'},'group_summary':metrics['group_summary'].to_dict(orient='records'),'risk_register':risks}
