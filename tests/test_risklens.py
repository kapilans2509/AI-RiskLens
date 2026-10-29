import pandas as pd
from risklens import make_sample_data,validate_candidate_data,score_candidates,calculate_fairness_metrics,build_risk_register,build_report

def test_sample_data_valid():
 d=make_sample_data();assert len(d)==20;assert validate_candidate_data(d)==[]
def test_score_and_threshold():
 d=make_sample_data();assert score_candidates(d,0).selected.all();assert not score_candidates(d,100).selected.any()
def test_validation():
 d=make_sample_data();d.loc[1,'candidate_id']=d.loc[0,'candidate_id'];d.loc[2,'skills_score']=101;e=validate_candidate_data(d);assert any('unique' in x for x in e);assert any('between 0 and 100' in x for x in e)
def test_metrics_and_risks():
 s=score_candidates(make_sample_data(),70);m=calculate_fairness_metrics(s);r=build_risk_register(s,m);assert len(m['group_summary'])==2;assert len(r)>=4;assert any(x['risk']=='Human oversight' for x in r)
def test_report_limitations():
 s=score_candidates(make_sample_data(),70);m=calculate_fairness_metrics(s);report=build_report(s,m,build_risk_register(s,m),70,'Group A');assert report['summary']['candidates_assessed']==20;assert report['methodology']['limitations']
