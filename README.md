# Campaign Performance Dashboard (Template A)

A Flask + pandas web app for campaign performance reporting with configurable KPI cards, filter controls, top-entity bar charts, and dual-axis trend analysis.

## What this app includes

- Dashboard page (`/`)
	- Date range + multi-select filters
	- KPI summary cards
	- Top KPI selector
	- Two configurable Top 10 entity charts
	- Dual-axis trend line chart with selectable left/right KPIs
	- Trend aggregation: daily, weekly (Monday start), monthly, quarterly, yearly
- Deep Dive page (`/deep-dive`)
	- Shared filter panel
	- Shared footer with date range + optional logo
- Config-driven behavior via `settings/dashboard_settings.json`
- Branding/theme configuration via `.env`
- Data source support:
	- SQLite (default)
	- MySQL

## Tech stack

- Python 3
- Flask
- pandas
- Chart.js (CDN in template)
- python-dotenv
- PyMySQL

## Project structure

```
main.py
backend/
	app_factory.py
	config.py
	routes/
		dashboard.py
	services/
		analytics_service.py
		dataframe_service.py
		db_service.py
		field_mapping_service.py
		kpi_calculation_service.py
		kpi_service.py
		mysql_service.py
		settings_service.py
	static/
		css/
		js/
		img/
	templates/
		dashboard.html
		deep_dive.html
		partials/
data/
	data.csv
settings/
	dashboard_settings.json
	field_mapping.json
```

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `.env` (or use defaults).
4. Run locally:

```bash
python main.py
```

5. Open:
	 - `http://127.0.0.1:5055/`
	 - `http://127.0.0.1:5055/deep-dive`

## Configuration

### Environment variables (`.env`)

Important keys used by the app:

- Data/backend
	- `SECRET_KEY`
	- `APP_PASSWORD` (optional, enables app sign-in when set)
	- `APP_PASSWORD_HASH` (optional, preferred over APP_PASSWORD when both are set)
	- `ENV_TYPE=dev|prod`
	- `STATIC_BUCKET` (used in `prod` if `STATIC_BASE_URL` is empty)
	- `STATIC_BASE_URL` (optional full CDN/base URL; when set in `prod`, it is preferred)
	- `DB_BACKEND=sqlite|mysql`
	- `SQLITE_DB_FILE`
	- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
	- `MYSQL_TABLE`, `MYSQL_STATE_TABLE`
	- `DASHBOARD_SETTINGS_FILE`
	- `FIELD_MAPPING_FILE`
	- `KPI_CACHE_TTL_SECONDS`
- KPI formatting
	- `KPI_CURRENCY_SYMBOL`
- Banner branding
	- `CLIENT_NAME`
	- `DASHBOARD_KICKER`
	- `DASHBOARD_BANNER_TITLE`
	- `LOGO_IMAGE_PATH`
	- `BANNER_GRADIENT_START`, `BANNER_GRADIENT_MID`, `BANNER_GRADIENT_END`
	- `DASHBOARD_FONT_FAMILY`
	- `KPI_LABEL_COLOR`, `KPI_VALUE_COLOR`
	- `KPI_LABEL_FONT_SIZE`, `KPI_VALUE_FONT_SIZE`
- Footer branding
	- `FOOTER_TEAM_NAME`
	- `FOOTER_LOGO_IMAGE_PATH`
	- `SHOW_FOOTER_LOGO=true|false`

Notes:
- `LOGO_IMAGE_PATH` and `FOOTER_LOGO_IMAGE_PATH` should be paths under `backend/static/`, for example `img/ogs-logo.gif`.
- `SHOW_FOOTER_LOGO` accepts: `true/false`, `1/0`, `yes/no`, `on/off`.
- Static serving mode:
	- `ENV_TYPE=dev`: templates serve assets via Flask local static route.
	- `ENV_TYPE=prod`: templates serve assets from GCS (`https://storage.googleapis.com/<STATIC_BUCKET>/static/...`) or from `STATIC_BASE_URL/static/...` when `STATIC_BASE_URL` is set.
- App sign-in mode:
	- If either `APP_PASSWORD` or `APP_PASSWORD_HASH` is configured, users must sign in at `/login` before accessing dashboard pages.
	- `APP_PASSWORD_HASH` should be a Werkzeug-compatible hash string.
### Dashboard settings (`settings/dashboard_settings.json`)

This JSON controls visible KPIs, selected filter fields, selected top-entity charts, and chart colors.

Key sections:

- `available_kpis`, `selected_kpis`
- `available_filter_fields`, `selected_filter_fields`
- `available_top_entity_charts`, `selected_top_entity_charts`
- `available_deep_dive_table_columns`, `selected_deep_dive_table_columns`
- `available_deep_dive_hierarchy_fields`, `selected_deep_dive_hierarchy_fields`
- `deep_dive_default_page_size` (positive integer; shown in page-size options together with `50`, `100`, `200`)
- `top_entity_chart_default_color`
- `top_entity_chart_colors` (per entity type and item value)
- `platform_chart_colors` (legacy compatibility for platform colors)

Current chart key options:

- `platform`
- `campaign_name`
- `campaign_group`
- `adname`
- `adset_name`

## Data and field mapping

The app reads data from the selected DB backend and applies a field mapping from `settings/field_mapping.json`.

Required logical fields include:

- `DATE`
- `CAMPAIGN_NAME`
- `AMOUNT_SPENT`
- `IMPRESSIONS`
- `CLICKS`
- `REACH`
- `CONVERSIONS`
- `LEADS`
- `VIDEO_VIEWS`
- `LIKES`
- `VIDEO_COMPLETION`

Optional filter/chart dimensions used in UI:

- `OBJECTIVE`
- `CAMPAIGN_GROUP`
- `PLATFORM`
- `AD_NAME`
- `ADSET_NAME`

### Mask data for dummy/sample use

Use the masking utility to anonymize text identifiers and perturb metrics while preserving schema compatibility with the dashboard:

```bash
python scripts/mask_sample_data.py --input data/data.csv
```

To write to a separate output file instead of replacing in place:

```bash
python scripts/mask_sample_data.py --input data/data.csv --output data/data.sample.csv
```

To update only label fields (campaign/group/audience/creative/objective/platform) with meaningful synthetic names and keep numeric sample metrics unchanged:

```bash
python scripts/mask_sample_data.py --input data/data.csv --text-only
```

Use an industry-specific naming tone when generating labels:

```bash
python scripts/mask_sample_data.py --input data/data.csv --text-only --naming-style retail
```

Available naming styles:

- `retail`
- `finance`
- `b2b`

## Routing

- `GET /` -> dashboard
- `GET /deep-dive` -> deep dive filter page
- `GET|POST /login` -> app password sign-in page
- `POST /logout` -> sign out and clear session auth

## Analytics behavior summary

- Top entity charts rank by a selected KPI and return top N (default N=6 in code).
- Dual-axis trend chart builds date buckets by selected granularity and plots two KPI series.
- Weekly bucket starts on Monday.
- KPI display uses compact formatting and currency symbol from environment settings.

## Deployment note

`main.py` includes an `entry_point(request)` function for Google Cloud Functions style deployment.

### Deployment script with .env

`deployment.py` reads deployment settings from `.env` and allows CLI overrides.
All keys present in that `.env` file are also uploaded to Cloud Functions runtime environment variables.

Common `.env` deployment keys:

- `DEPLOY_PROJECT_ID`
- `DEPLOY_REGION`
- `DEPLOY_FUNCTION_NAME`
- `DEPLOY_ENTRY_POINT`
- `DEPLOY_RUNTIME`
- `DEPLOY_BUCKET_NAME`
- `DEPLOY_BUCKET_LOCATION`
- `DEPLOY_STATIC_DIR`
- `DEPLOY_SOURCE_DIR`
- `DEPLOY_ALLOW_UNAUTHENTICATED`

Run deployment using `.env` defaults:

```bash
python deployment.py --env-file .env
```

Override a value when needed:

```bash
python deployment.py --env-file .env --region asia-south1
```

Preview deployment without executing gcloud actions:

```bash
python deployment.py --env-file .env --dry-run
```

Print a compact resolved-settings summary (works with or without dry-run):

```bash
python deployment.py --env-file .env --dry-run --dry-run-summary
```

## Troubleshooting

- If UI changes do not appear, hard refresh browser to bypass cached static files.
- If using MySQL, confirm connection values in `.env` and table names match.
- If filters/charts show empty results, validate field names in `settings/field_mapping.json` against source data.
