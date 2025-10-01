from datetime import datetime, timedelta
from timesheet import export_monthly_report_json

def main():
    today = datetime.now()
    last_month_date = today.replace(day=1) - timedelta(days=1)

    year = last_month_date.year
    month = last_month_date.month

    result = export_monthly_report_json(year, month)
    month_name = last_month_date.strftime("%B")

    print(f"✅ Export für {month_name} {year} erfolgreich!")
    print(result)

if __name__ == "__main__":
    main()
