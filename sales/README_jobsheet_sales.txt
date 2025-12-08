CARGOCHAINS - JOBSHEET SUBMODULE (inside app `sales`)
================================================

Files in this package:
- sales/jobs.py                -> models: Job, JobCostLine, JobStatus
- sales/forms_jobsheet.py      -> forms: JobForm, JobCostLineForm, JobCostLineFormSet
- sales/views/jobsheet.py      -> view: JobSheetView
- templates/sales/jobsheet_split.html

HOW TO INSTALL (high level):

1. Copy files
   - Put `sales/jobs.py` into your existing `sales` app.
   - Put `sales/forms_jobsheet.py` into the same app.
   - Put `sales/views/jobsheet.py` under your existing `sales/views/` package.
   - Put `templates/sales/jobsheet_split.html` into your templates folder.

2. Wire URL
   In `sales/urls.py` add:

       from sales.views.jobsheet import JobSheetView

       urlpatterns += [
           path("jobsheets/", JobSheetView.as_view(), name="jobsheet"),
       ]

3. Adjust ForeignKey to your real Customer PO model
   In `sales/jobs.py`, update:

       purchase_order = models.ForeignKey(
           "sales.CustomerPO",  # TODO: ganti ke model PO customer yang benar
           on_delete=PROTECT,
           related_name="job_cost_lines",
       )

4. NumberSequence
   Make sure you have NumberSequence row for:
   - app = "sales"
   - code = "JOBSHEET"

5. Migrations
   Run:

       python manage.py makemigrations sales
       python manage.py migrate

6. Access URL:
   /sales/jobsheets/  (or whatever prefix your `sales` app uses)
