import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import os
import sys

output_dir = os.path.join(os.path.expanduser("~"), "Downloads", "samsung_ce_analysis")
os.makedirs(output_dir, exist_ok=True)
os.chdir(output_dir)

np.random.seed(42)

# 1. DEFINICIJA ASORTIMANA I MALOPRODAJNIH PARTNERA (CE SEAD)
products = [
    {"SKU": "QE65S95D", "Product_Name": "OLED 65\" S95D 4K Smart TV", "Category": "TV", "Regular_Price": 2299.00, "Base_Daily_Demand": 1.4},
    {"SKU": "QE55QN85D", "Product_Name": "Neo QLED 55\" QN85D 4K TV", "Category": "TV", "Regular_Price": 1299.00, "Base_Daily_Demand": 2.2},
    {"SKU": "UE50DU7172", "Product_Name": "Crystal UHD 50\" DU7172 TV", "Category": "TV", "Regular_Price": 479.00, "Base_Daily_Demand": 4.8},
    {"SKU": "RB38C7B6AS9", "Product_Name": "Bespoke Hladnjak 387L", "Category": "Home Appliances", "Regular_Price": 899.00, "Base_Daily_Demand": 1.1},
    {"SKU": "WW90DG6U85L", "Product_Name": "Perilica rublja AI Ecobubble 9kg", "Category": "Home Appliances", "Regular_Price": 649.00, "Base_Daily_Demand": 2.5},
    {"SKU": "VS20B75AGR5", "Product_Name": "Jet 75E Štapni usisavač", "Category": "Home Appliances", "Regular_Price": 399.00, "Base_Daily_Demand": 3.1},
    {"SKU": "LS32BG850N", "Product_Name": "Odyssey Neo G8 32\" Gaming Monitor", "Category": "Monitors", "Regular_Price": 1099.00, "Base_Daily_Demand": 0.9},
    {"SKU": "LS27DG500E", "Product_Name": "Odyssey G5 27\" QHD Monitor", "Category": "Monitors", "Regular_Price": 279.00, "Base_Daily_Demand": 4.2},
]

retailers = ["Sancta Domenica", "Elipso", "Harvey Norman", "eKupi"]
dates = pd.date_range(end="2026-11-19", periods=90, freq="D")

rows = []
for retailer in retailers:
    for prod in products:
        stock = np.random.randint(45, 95)
        for day_idx, current_date in enumerate(dates):
            # Tri promotivna vala tijekom 90 dana
            is_promo = int((15 <= day_idx <= 25) or (48 <= day_idx <= 58) or (78 <= day_idx <= 88))
            selling_price = round(prod["Regular_Price"] * 0.82, 2) if is_promo else prod["Regular_Price"]

            # Simulacija Dead Inventoryja (visoka zaliha, gotovo nula prodaje)
            if (prod["SKU"] == "RB38C7B6AS9" and retailer == "Harvey Norman") or \
               (prod["SKU"] == "LS32BG850N" and retailer == "Sancta Domenica"):
                units_sold = 1 if day_idx in [12, 45] else 0
                stock = 64
            else:
                multiplier = 2.35 if is_promo else 1.0
                weekend_boost = 1.25 if current_date.weekday() >= 5 else 1.0
                expected = prod["Base_Daily_Demand"] * multiplier * weekend_boost
                units_sold = np.random.poisson(expected)

                # Simulacija Stockout rizika na najprodavanijim modelima
                if (prod["SKU"] == "UE50DU7172" and retailer == "Elipso" and day_idx > 75):
                    stock = max(3, stock - units_sold)
                elif (prod["SKU"] == "LS27DG500E" and retailer == "eKupi" and day_idx > 78):
                    stock = max(4, stock - units_sold)
                else:
                    stock = max(8, stock - units_sold)
                    if stock < 15 and day_idx < 75:
                        stock += 45  # redovna nadopuna skladišta prije zadnja 2 tjedna

            rows.append({
                "Date": current_date.strftime("%Y-%m-%d"),
                "Retailer": retailer,
                "Category": prod["Category"],
                "SKU": prod["SKU"],
                "Product_Name": prod["Product_Name"],
                "Regular_Price_EUR": prod["Regular_Price"],
                "Selling_Price_EUR": selling_price,
                "Promo_Flag": is_promo,
                "Units_Sold": units_sold,
                "Revenue_EUR": round(units_sold * selling_price, 2),
                "Stock_On_Hand": stock
            })

df_raw = pd.DataFrame(rows)

# UBACIVANJE NAMJERNIH GREŠAKA ZA VALIDACIJU (Promo Data Hygiene)
# 1) Pogrešne akcijske cijene (akcijska cijena veća od redovne)
bad_idx = df_raw[df_raw["Promo_Flag"] == 1].sample(6, random_state=42).index
df_raw.loc[bad_idx, "Selling_Price_EUR"] = df_raw.loc[bad_idx, "Regular_Price_EUR"] * 1.05
# 2) Duplikati zapisa
df_raw = pd.concat([df_raw, df_raw.iloc[:5]], ignore_index=True)
df_raw.to_csv("ce_retail_raw.csv", index=False)

# ==============================================================================
# ANALIZA 1: VALIDACIJA PROMOTIVNIH PODATAKA (Promo Data Hygiene)
# ==============================================================================
duplicates = df_raw[df_raw.duplicated(subset=["Date", "Retailer", "SKU"], keep="first")].copy()
duplicates["Issue_Type"] = "Duplicate Record"

price_errors = df_raw[(df_raw["Promo_Flag"] == 1) & (df_raw["Selling_Price_EUR"] >= df_raw["Regular_Price_EUR"])].copy()
price_errors["Issue_Type"] = "Promo Price >= Regular Price"

audit_issues = pd.concat([duplicates, price_errors], ignore_index=True)
audit_issues.to_csv("promo_audit_issues.csv", index=False)
print(f"[1. PROMO AUDIT] Pronađeno {len(audit_issues)} grešaka u podacima (spremljeno u promo_audit_issues.csv).")

# Čišćenje podataka za daljnju analizu i Power BI
df_clean = df_raw.drop_duplicates(subset=["Date", "Retailer", "SKU"], keep="first").copy()
invalid_price_mask = (df_clean["Promo_Flag"] == 1) & (df_clean["Selling_Price_EUR"] >= df_clean["Regular_Price_EUR"])
df_clean.loc[invalid_price_mask, "Selling_Price_EUR"] = round(df_clean.loc[invalid_price_mask, "Regular_Price_EUR"] * 0.82, 2)
df_clean["Revenue_EUR"] = round(df_clean["Units_Sold"] * df_clean["Selling_Price_EUR"], 2)
df_clean.to_csv("ce_retail_clean.csv", index=False)

# ==============================================================================
# ANALIZA 2: UČINAK PROMOCIJA PO KATEGORIJAMA (Promotional Uplift)
# ==============================================================================
uplift = df_clean.groupby(["Category", "Promo_Flag"])["Units_Sold"].mean().unstack()
uplift.columns = ["Regular_Avg_Daily_Units", "Promo_Avg_Daily_Units"]
uplift["Uplift_Pct"] = round(((uplift["Promo_Avg_Daily_Units"] - uplift["Regular_Avg_Daily_Units"]) / uplift["Regular_Avg_Daily_Units"]) * 100, 1)
print("\n[2. PROMOTIONAL UPLIFT PO KATEGORIJAMA]")
print(uplift)

# ==============================================================================
# ANALIZA 3 & 4: STOCKOUT RISK & DEAD INVENTORY (Zadnjih 14 / 30 dana)
# ==============================================================================
df_clean["Date"] = pd.to_datetime(df_clean["Date"])
max_date = df_clean["Date"].max()

last_14d = df_clean[df_clean["Date"] > (max_date - pd.Timedelta(days=14))]
last_30d = df_clean[df_clean["Date"] > (max_date - pd.Timedelta(days=30))]

avg_daily_14d = last_14d.groupby(["Retailer", "Category", "SKU", "Product_Name"])["Units_Sold"].mean().reset_index(name="Avg_Daily_Sales_14d")
sales_30d = last_30d.groupby(["Retailer", "SKU"])["Units_Sold"].sum().reset_index(name="Units_Sold_30d")
latest_stock = df_clean[df_clean["Date"] == max_date][["Retailer", "SKU", "Stock_On_Hand"]]

inventory_health = avg_daily_14d.merge(sales_30d, on=["Retailer", "SKU"]).merge(latest_stock, on=["Retailer", "SKU"])
inventory_health["Days_of_Cover"] = np.where(
    inventory_health["Avg_Daily_Sales_14d"] > 0,
    round(inventory_health["Stock_On_Hand"] / inventory_health["Avg_Daily_Sales_14d"], 1),
    999.0
)

def classify_stock(row):
    if row["Days_of_Cover"] < 7 and row["Avg_Daily_Sales_14d"] >= 2.0:
        return "Stockout Risk (< 7 days)"
    elif row["Stock_On_Hand"] >= 50 and row["Units_Sold_30d"] <= 2:
        return "Dead Inventory (30d+ stagnant)"
    return "Healthy"

inventory_health["Inventory_Status"] = inventory_health.apply(classify_stock, axis=1)
inventory_health.to_csv("inventory_health_summary.csv", index=False)

print("\n[3 & 4. RIZIČNE ZALIHE (STOCKOUT & DEAD INVENTORY)]")
print(inventory_health[inventory_health["Inventory_Status"] != "Healthy"][["Retailer", "SKU", "Product_Name", "Stock_On_Hand", "Days_of_Cover", "Inventory_Status"]])

# ==============================================================================
# GENERIRANJE PNG GRAFOVA ZA GITHUB README
# ==============================================================================
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(uplift.index))
width = 0.35
ax.bar(x - width/2, uplift["Regular_Avg_Daily_Units"], width, label="Redovna prodaja", color="#64748B")
ax.bar(x + width/2, uplift["Promo_Avg_Daily_Units"], width, label="Promocija (-18%)", color="#1428A0")
ax.set_title("Prosječna dnevna prodaja po trgovini: Redovno vs. Promocija", fontsize=12, fontweight="bold")
ax.set_ylabel("Prosječno prodanih komada / dan")
ax.set_xticks(x)
ax.set_xticklabels(uplift.index)
ax.legend()
for i, pct in enumerate(uplift["Uplift_Pct"]):
    ax.text(i + width/2, uplift["Promo_Avg_Daily_Units"].iloc[i] + 0.12, f"+{pct}%", ha="center", fontweight="bold", color="#1428A0")
plt.tight_layout()
plt.savefig("chart_promo_uplift.png", dpi=300)
print("\nGrafikon spremljen kao chart_promo_uplift.png")