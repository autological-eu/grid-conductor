import copy
import csv
import tempfile
import unittest
from pathlib import Path
from forward_learning_curves_2025 import validate,aggregate,hours,render


def fixture():
    records=[]
    for month in range(1,13):
        for i in range(101):
            row=dict(month=month,iteration=i,training_hours=hours(month),training_zone_mae=[float(month),float(month+2)])
            if month<12:row.update(validation_hours=hours(month+1),validation_zone_mae=[float(month+1),float(month+3)])
            records.append(row)
    return dict(model_id='unit_fixture',score_solver_id='unit_fixture',audit_status='passed',
                modeled_zones=['A','B'],observed_zones=['A','B'],records=records)


class LearningCurveTests(unittest.TestCase):
    def test_complete_calendar_points_and_matched_weighting(self):
        rows=validate(fixture(),2,2);self.assertEqual(len(rows),1212)
        self.assertEqual(sum(hours(m) for m in range(1,13)),8760)
        training,training_hours=aggregate(rows,100,'training',True)
        validation,validation_hours=aggregate(rows,100,'validation')
        self.assertEqual(training_hours,8016);self.assertEqual(validation_hours,8016)
        self.assertAlmostEqual(training,validation)
        self.assertEqual(aggregate(rows,0,'training')[1],8760)

    def test_missing_duplicate_and_december_validation_rejected(self):
        for mutation in ['missing','duplicate','december']:
            data=fixture()
            if mutation=='missing':data['records'].pop()
            if mutation=='duplicate':data['records'].append(copy.deepcopy(data['records'][0]))
            if mutation=='december':data['records'][-1].update(validation_hours=744,validation_zone_mae=[1,2])
            with self.assertRaises(ValueError):validate(data,2,2)

    def test_missing_coverage_and_unaudited_export_rejected(self):
        for mutation in ['coverage','nonfinite','audit','model']:
            data=fixture()
            if mutation=='coverage':data['records'][0]['validation_hours']=720
            if mutation=='nonfinite':data['records'][0]['training_zone_mae'][0]=float('nan')
            if mutation=='audit':data['audit_status']='pending'
            if mutation=='model':data['model_id']=None
            with self.assertRaises(ValueError):validate(data,2,2)

    def test_real_plot_export_and_no_fabricated_december_validation(self):
        data=fixture();data['modeled_zones']=[f'Z{i}' for i in range(48)]
        data['observed_zones']=data['modeled_zones'][:41]
        for row in data['records']:
            row['training_zone_mae']=[float(row['month'])]*41
            if row['month']<12:row['validation_zone_mae']=[float(row['month']+1)]*41
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/'unit-fixture-only'
            render(data,prefix)
            svg=prefix.with_name(prefix.name+'-months.svg').read_text()
            self.assertIn('Dec fit · validation unavailable',svg)
            with prefix.with_name(prefix.name+'-monthly.csv').open() as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),1212)
            self.assertTrue(all(row['validation_mae']=='' for row in rows if row['fit_month']=='12'))


if __name__=='__main__':unittest.main()
