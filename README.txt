Instructions for using the CEFET survey data and KPIs in Power BI
================================================================

Contents of this package:

1. `cefet_clean.csv` – The cleaned dataset derived from the CEFET survey. This CSV already
   consolidates the two header rows, normalizes Likert scales, converts checkboxes to 1/0,
   and calculates aggregated indices such as infrastructure, accessibility, entrepreneurial
   profile, and risk of dropout.  Use this file as your data source when importing into
   Power BI.

2. `power_query_m.txt` – A Power Query (M) script that demonstrates how you could import
   the original Excel into Power BI and perform the same cleaning steps.  If you start from
   the original Excel instead of the provided CSV, paste this script into the
   Power Query editor to transform your data.

3. `dax_measures.txt` – A collection of DAX measures that implement the KPIs discussed in
   the analysis.  Create these measures in Power BI to compute totals, averages, deltas and
   comparisons.  They follow best practices (ALLSELECTED, BLANK handling) and allow
   side‑by‑side comparison of courses or institutions.

4. `dax_columns.txt` – Example DAX calculated columns for bucketing risk and infrastructure
   scores, plus period extraction (year and month) from the timestamp.

### Using this package

1. Launch Power BI Desktop and choose `Get Data` → `CSV`. Select the provided
   `cefet_clean.csv` file and load it into the report.  Alternatively, choose `Get Data` →
   `Excel` and apply the Power Query script from `power_query_m.txt` in the Advanced Editor.

2. In the `Model` view, ensure that numeric fields are set to type Whole Number or Decimal
   Number and date/time fields to Date/Time.  You can create a Date table or use the
   provided period columns for filtering.

3. Copy the DAX expressions from `dax_measures.txt` into new measures in Power BI (Home →
   New Measure).  Give each measure the same name as in the file (e.g., `Respondentes`).
   These measures compute KPIs such as average infrastructure, entrepreneurial index,
   engagement, dropout risk, comparison deltas, and Top‑N reasons for staying or leaving.

4. If desired, add the calculated columns from `dax_columns.txt` to the `Fato_Respostas` table
   by creating new columns (Modeling → New Column). These create categorical levels for
   infrastructure and risk.

5. Build your report: Create cards to display totals and averages, clustered bar charts for
   distributions by course or teaching model, stacked bar charts or heatmaps for drop‑out
   reasons, and radar charts for the entrepreneurial sub‑dimensions.  Use slicers on the
   course, institution, year of entry, and teaching model fields for filtering.  Optionally,
   create two disconnected tables for comparison (Comp_Curso and Comp_Instituicao) to
   enable side‑by‑side comparison using the `TREATAS` pattern found in the DAX measures.

This package provides all necessary data and DAX logic to recreate the KPIs and visuals
that were previously developed in JavaScript/HTML.  You can extend it further in Power BI
Desktop by adding more measures or adjusting the visuals to suit your needs.
