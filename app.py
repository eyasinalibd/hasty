import streamlit as st
import pandas as pd
import io

# --- Page Config ---
st.set_page_config(page_title="HASTY", layout="wide")

# --- Initialize session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- Login Page ---
if not st.session_state.logged_in:
    st.title("🔐 HASTY - Login\n **Hectare, Annual Sales, Technology, Yield (HASTY)**")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

# --- After Login ---
if st.session_state.logged_in:
    # Sidebar navigation
    st.sidebar.title("⚙️ Menu")
    option = st.sidebar.radio("Select Options:", ["About HASTY", "Analysis"])

    # --- Page: About HASTY ---
    if option == "About HASTY":
        st.title("ℹ️ About HASTY System")
        st.markdown(
            """
            HASTY is a system to help generate indicator outputs from survey results with proper reporting requirements, 
            particularly for **Hectare, Annual Sale, Technology, and Yield (HASTY)** reporting to meet donor requirements. 
            This system helps you reduce analysis time and quickly generate all your reporting outputs in the Indicator Tracking Table layout.

            **⚙️ How it Works**
            1. Use the standard reporting template to update your survey results. 
            2. Upload the Excel file in the system (must include sheets: `participants` and `technology`).
            3. Click the **Run Analysis and Generate Excel** button to produce your required output.
            4. After analysis, download the Excel file and use it directly for your ITT reporting.
            """
        )

        template_url = "https://github.com/eyasinalibd/hasty/blob/main/survey_update.xlsx?raw=true"
       
        st.markdown(f"[📥 Download Reporting Template]({template_url})")

    # --- Page: Analysis ---
    elif option == "Analysis":
        st.title("Hectare, Annual Sales, Technology, Yield (HASTY)")
        st.subheader("Commodity & Technology Data Analysis")
        st.markdown(
            "Upload your HASTY Excel file (must contain sheets: `participants` and `technology`). "
            "The app will produce an Excel workbook with commodity sheets and a Technology sheet."
        )

        @st.cache_data
        def read_excel(file) -> pd.DataFrame:
            return pd.read_excel(file)

        # --- Commodity Analysis Function ---
        def compute_for_commodity(df_comm: pd.DataFrame) -> pd.DataFrame:
            df = df_comm.copy()
            numeric_cols = ["male", "female", "totalmf", "Age_15-29_ratio",
                            "production_area", "total_production",
                            "quantity_sales", "value_sales", "per_dollar_rate"]
            for c in numeric_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

            # Helper functions
            def prod_contrib(row, sex_count_col):
                tp_unit = str(row.get('tp_unit', '')).strip().lower()
                commodity_type = str(row.get('commodity_type', '')).strip().lower()
                count = row.get(sex_count_col, 0)
                tp = row.get('total_production', 0)
                if commodity_type == "livestock":
                    return count * tp
                else:
                    if tp_unit == 'kg':
                        return (count * tp) / 1000.0
                    else:
                        return count * tp

            def area_contrib(row, sex_count_col):
                unit = str(row.get('parea_unit', '')).strip().lower()
                count = row.get(sex_count_col, 0)
                pa = row.get('production_area', 0)
                if unit == 'dec':
                    return (count * pa) / 247.10514233241506
                elif unit == 'acre':
                    return (count * pa) * 0.4046
                else:
                    return (count * pa)

            def volume_sales(row, sex_count_col):
                q_unit = str(row.get('qsales_unit', '')).strip().lower()
                comm_type = str(row.get('commodity_type', '')).strip().lower()
                count = row.get(sex_count_col, 0)
                qty = row.get('quantity_sales', 0)
                if comm_type == "livestock":
                    return count * qty
                else:
                    if q_unit == "kg":
                        return (count * qty) / 1000.0
                    else:
                        return count * qty

            def value_sales(row, sex_count_col):
                count = row.get(sex_count_col, 0)
                val = row.get("value_sales", 0)
                per_rate = row.get("per_dollar_rate", 1)
                return round((count * val) / per_rate, 2)

            df['male_prod_contrib'] = df.apply(lambda r: prod_contrib(r, 'male'), axis=1)
            df['female_prod_contrib'] = df.apply(lambda r: prod_contrib(r, 'female'), axis=1)
            df['male_area_contrib'] = df.apply(lambda r: area_contrib(r, 'male'), axis=1)
            df['female_area_contrib'] = df.apply(lambda r: area_contrib(r, 'female'), axis=1)
            df['male_vol_sales'] = df.apply(lambda r: volume_sales(r, 'male'), axis=1)
            df['female_vol_sales'] = df.apply(lambda r: volume_sales(r, 'female'), axis=1)
            df['male_val_sales'] = df.apply(lambda r: value_sales(r, 'male'), axis=1)
            df['female_val_sales'] = df.apply(lambda r: value_sales(r, 'female'), axis=1)

            # Totals
            male_prod_sum = df['male_prod_contrib'].sum()
            female_prod_sum = df['female_prod_contrib'].sum()
            total_prod_sum = male_prod_sum + female_prod_sum

            male_area_sum = df['male_area_contrib'].sum()
            female_area_sum = df['female_area_contrib'].sum()
            total_area_sum = male_area_sum + female_area_sum

            male_participants = df['male'].sum()
            female_participants = df['female'].sum()
            total_participants = male_participants + female_participants

            male_vol_sum = df['male_vol_sales'].sum()
            female_vol_sum = df['female_vol_sales'].sum()
            total_vol_sum = male_vol_sum + female_vol_sum

            male_val_sum = df['male_val_sales'].sum()
            female_val_sum = df['female_val_sales'].sum()
            total_val_sum = male_val_sum + female_val_sum

            # Age ratio
            if df['totalmf'].sum() > 0:
                age_ratio = (df['Age_15-29_ratio'] * df['totalmf']).sum() / df['totalmf'].sum()
            else:
                age_ratio = df['Age_15-29_ratio'].mean() if len(df) > 0 else 0
            age_frac = float(age_ratio) / 100.0 if pd.notna(age_ratio) else 0.0

            # Build Results
            rows = []
            commodity_name = df_comm['commodity_name'].iloc[0]

            commodity_type = str(df_comm['commodity_type'].iloc[0]).strip().lower()
            # Overall Yield
            overall_yield = total_prod_sum / total_area_sum if total_area_sum != 0 else 0
            rows.append((commodity_name,commodity_type, 'Overall', 'Yield', round(overall_yield, 2), 'Yield'))

            # Production, Area, Participants, Value, Volume
            sections = ['Total Production', 'Production Area', 'Total Number of Participants', 'Value of Sales', 'Volume of Sales']
            for sec in sections:
                if sec == 'Total Production':
                    values = [total_prod_sum, male_prod_sum, female_prod_sum, total_prod_sum, total_prod_sum*age_frac, total_prod_sum*(1-age_frac)]
                    unit = 'tonne_or_unit'
                elif sec == 'Production Area':
                    values = [total_area_sum, male_area_sum, female_area_sum, total_area_sum, total_area_sum*age_frac, total_area_sum*(1-age_frac)]
                    unit = 'ha_or_unit'
                elif sec == 'Total Number of Participants':
                    values = [total_participants, male_participants, female_participants, total_participants, total_participants*age_frac, total_participants*(1-age_frac)]
                    unit = 'count'
                elif sec == 'Value of Sales':
                    values = [total_val_sum, male_val_sum, female_val_sum, total_val_sum, total_val_sum*age_frac, total_val_sum*(1-age_frac)]
                    unit = 'USD'
                else: # Volume of Sales
                    values = [total_vol_sum, male_vol_sum, female_vol_sum, total_vol_sum, total_vol_sum*age_frac, total_vol_sum*(1-age_frac)]
                    unit = 'tonne_or_unit'

                disagg = ['Sex', 'Male', 'Female', 'Age', '15-29', '30+']
                for d, v in zip(disagg, values):
                    rows.append((commodity_name, commodity_type, sec, d, round(v,2), unit))

            return pd.DataFrame(rows, columns=['Commodity_Name','Commodity_type', 'Sections', 'Disaggregate', 'Result', 'Unit'])

        # --- Corrected Technology Analysis Function ---
        def compute_technology(df_tech, df_part):
            rows = []

            # Smallholder Producer, Sex, Age
            male_total = round(
                (df_tech.loc[df_tech['items'] == 'Ag_unique_M_Total', 'value'].values[0] *
                 df_tech.loc[df_tech['items'] == 'overall_ag_Tech_Pecent', 'value'].values[0] / 100) +
                (df_tech.loc[df_tech['items'] == 'Liv_unique_M_Total', 'value'].values[0] *
                 df_tech.loc[df_tech['items'] == 'overall_liv_Tech_Pecent', 'value'].values[0] / 100)
            )
            female_total = round(
                (df_tech.loc[df_tech['items'] == 'Ag_unique_F_Total', 'value'].values[0] *
                 df_tech.loc[df_tech['items'] == 'overall_ag_Tech_Pecent', 'value'].values[0] / 100) +
                (df_tech.loc[df_tech['items'] == 'Liv_unique_F_Total', 'value'].values[0] *
                 df_tech.loc[df_tech['items'] == 'overall_liv_Tech_Pecent', 'value'].values[0] / 100)
            )
            total = male_total + female_total
            age_ratio = df_tech.loc[df_tech['items'] == 'Overall_Age_15-29_ratio', 'value'].values[0] / 100

            rows.append(('Smallholder Producer', total))
            rows.append(('Sex', total))
            rows.append(('Male', male_total))
            rows.append(('Female', female_total))
            rows.append(('Age', total))
            rows.append(('15-29', round(total * age_ratio, 0)))
            rows.append(('30+', round(total * (1 - age_ratio), 0)))

            # --- Technology items ---
            # --- Technology items ---
            tech_items = df_tech[df_tech['category'].notna() & df_tech['items'].notna()]

            for _, r in tech_items.iterrows():
                item_name = r['items']
                cat = str(r['category']).lower()
                item_percent = r['value'] / 100
                base = 0

                # --- FIX: handle livestock management separately ---
                if item_name.lower() == 'livestock management':
                    base = df_tech.loc[df_tech['items'] == 'Livestock_unique_MF_Total', 'value'].values[0] \
                           * df_tech.loc[df_tech['items'] == 'overall_liv_Tech_Pecent', 'value'].values[0] / 100
                else:
                    if cat == 'agriculture':
                        base = df_tech.loc[df_tech['items'] == 'Ag_unique_MF_Total', 'value'].values[0] \
                               * df_tech.loc[df_tech['items'] == 'overall_ag_Tech_Pecent', 'value'].values[0] / 100
                    elif cat == 'livestock':
                        base = df_tech.loc[df_tech['items'] == 'Livestock_unique_MF_Total', 'value'].values[0] \
                               * df_tech.loc[df_tech['items'] == 'overall_liv_Tech_Pecent', 'value'].values[0] / 100
                    elif cat == 'wild':
                        base = df_tech.loc[df_tech['items'] == 'Wildcaught_unique_MF_Total', 'value'].values[0]
                    elif cat == 'aquaculture':
                        base = df_tech.loc[df_tech['items'] == 'Aqua_unique_MF_Total', 'value'].values[0]
                    elif cat == 'naturalresource':
                        base = df_tech.loc[df_tech['items'] == 'NaturalR_unique_MF_Total', 'value'].values[0]

                if base > 0:
                    result = round(base * item_percent, 0)
                    rows.append((item_name, result))

            # Add commodity total participants from participants dataset
            for comm in df_part['commodity_name'].unique():
                total_comm = df_part.loc[df_part['commodity_name'] == comm, 'totalmf'].sum()
                rows.append((f'Total Participants - {comm}', total_comm))

            return pd.DataFrame(rows, columns=['Disaggregate/Technology', 'Result'])


        # --- Hectare Analysis Function ---
        def compute_hectare(all_sheets, df_technology):
            # Step 1 & 2: Pull Total Production Area for agriculture commodities
            hectare_rows = []
            commodities_ag = [c for c, df in all_sheets.items()
                              if 'Commodity_type' in df.columns and df['Commodity_type'].iloc[0] == 'agriculture']

            for comm in commodities_ag:
                df_comm = all_sheets[comm]
                total_area = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                         (df_comm['Disaggregate'] == 'Sex'), 'Result'].sum()
                male_area = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                        (df_comm['Disaggregate'] == 'Male'), 'Result'].sum()
                female_area = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                          (df_comm['Disaggregate'] == 'Female'), 'Result'].sum()
                age_area = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                       (df_comm['Disaggregate'] == 'Age'), 'Result'].sum()
                age_15_29 = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                        (df_comm['Disaggregate'] == '15-29'), 'Result'].sum()
                age_30_plus = df_comm.loc[(df_comm['Sections'] == 'Production Area') &
                                          (df_comm['Disaggregate'] == '30+'), 'Result'].sum()
                total_participants = df_comm.loc[(df_comm['Sections'] == 'Total Number of Participants') &
                                                 (df_comm['Disaggregate'] == 'Sex'), 'Result'].sum()

                hectare_rows.append({
                    'Commodity': comm,
                    'Total participants': total_participants,
                    'Total Production Area': total_area,
                    'Total Production Area Male': male_area,
                    'Total Production Area Female': female_area,
                    'Total Production Area Age': age_area,
                    'Total Production Area 15-29': age_15_29,
                    'Total Production Area 30+': age_30_plus
                })

            df_hectare = pd.DataFrame(hectare_rows)

            # Step 3: Summary values for Crop land, Sex, Male, Female, Age, 15-29, 30+
            summary = {
                'Crop land': df_hectare['Total Production Area'].sum(),
                'Sex': df_hectare['Total Production Area'].sum(),
                'Male': df_hectare['Total Production Area Male'].sum(),
                'Female': df_hectare['Total Production Area Female'].sum(),
                'Age': df_hectare['Total Production Area Age'].sum(),
                '15-29': df_hectare['Total Production Area 15-29'].sum(),
                '30+': df_hectare['Total Production Area 30+'].sum()
            }

            # Step 4: Technology % applied to Crop land
            tech_rows = []
            for _, r in df_technology.iterrows():
                if str(r['category']).strip().lower() == 'agriculture':
                    tech_rows.append({
                        'Disaggregate/Technology': r['items'],
                        'Result': round(summary['Crop land'] * r['value'] / 100, 2)
                    })
            df_tech_calc = pd.DataFrame(tech_rows)

            # Combine hectare summary + technology applied
            hectare_final_rows = []

            # Add indicator summary
            for k, v in summary.items():
                hectare_final_rows.append({'Disaggregate/Technology': k, 'Result': round(v, 2)})

            # Add technology applied
            for _, row in df_tech_calc.iterrows():
                hectare_final_rows.append({'Disaggregate/Technology': row['Disaggregate/Technology'],
                                           'Result': row['Result']})

            # Add commodity-wise participants
            for _, row in df_hectare.iterrows():
                hectare_final_rows.append({'Disaggregate/Technology': row['Commodity'],
                                           'Result': row['Total participants']})

            df_hectare_final = pd.DataFrame(hectare_final_rows)
            return df_hectare_final


        # --- File Upload ---
        uploaded_file = st.file_uploader("📂 Upload survey_update.xlsx (sheets: participants + technology)", type=['xlsx'])
        if uploaded_file is not None:
            try:
                df_participants = pd.read_excel(uploaded_file, sheet_name="participants")
                df_technology = pd.read_excel(uploaded_file, sheet_name="technology")
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()

            df_participants['commodity_name'] = df_participants['commodity_name'].astype(str)
            commodities = df_participants['commodity_name'].unique().tolist()
            st.sidebar.subheader("Detected commodities:")
            for c in commodities:
                st.sidebar.write(f"- {c}")

            if st.button("Run Analysis and Generate Excel"):
                all_sheets = {}
                progress = st.progress(0)

                # Commodity sheets
                for i, comm in enumerate(commodities):
                    sub = df_participants[df_participants['commodity_name']==comm]
                    all_sheets[comm] = compute_for_commodity(sub)
                    progress.progress(int((i+1)/len(commodities)*100))

                # Technology sheet
                all_sheets['Technology'] = compute_technology(df_technology, df_participants)
                     # --- Add Hectare sheet ---
                df_hectare_final = compute_hectare(all_sheets, df_technology)
                all_sheets['Hectare'] = df_hectare_final

                # Create Excel in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    for sheet_name, sheet_df in all_sheets.items():
                        safe_name = sheet_name[:31]
                        sheet_df.to_excel(writer, sheet_name=safe_name, index=False)
                output.seek(0)

                st.success("✅ Analysis completed. Download the Excel file below.")
                st.download_button(
                    "📥 Download Results",
                    data=output.getvalue(),
                    file_name='commodity_technology_analysis.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            st.markdown("---")
            st.subheader("Preview of uploaded participants data (first 20 rows)")
            st.dataframe(df_participants.head(20))

            st.markdown("---")
            st.subheader("Preview of uploaded technology data (first 30 rows)")
            st.dataframe(df_technology.head(31))


        else:
            st.info("Please upload the HASTY Excel file to begin.")

