import streamlit as st
import pandas as pd
import math

sheets = ['Races', 'Roles', 'FMoves']
joined = {}
for sheet in sheets:
    joined[sheet] = pd.read_excel(f'{sheet}.xlsx')
joined['Roles'] = joined['Roles'].rename(columns={'group': 'races'})
joined['Roles']['races'] = joined['Roles']['races'].astype(str).str.replace(' | ', ',', regex=False)

st.set_page_config(layout="wide")

def render_selection_buttons(df, id_col, name_col, session_key, label, buttons_per_row=12):
    """
    Modular function to render selection buttons for any dataframe
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = []
    
    # st.write(f"Select {label}:")
    n_rows = math.ceil(len(df) / buttons_per_row)
    
    for r in range(n_rows):
        start_idx = r * buttons_per_row
        end_idx = min((r + 1) * buttons_per_row, len(df))
        cols = st.columns(end_idx - start_idx)
        
        for idx, col_idx in enumerate(range(start_idx, end_idx)):
            item_id = df.loc[col_idx, id_col]
            item_name = df.loc[col_idx, name_col]
            is_selected = item_id in st.session_state[session_key]
            button_label = f"✅ {item_name}" if is_selected else item_name
            
            if cols[idx].button(button_label, key=f"{session_key}_{item_id}"):
                if is_selected:
                    st.session_state[session_key].remove(item_id)
                else:
                    st.session_state[session_key].append(item_id)
                st.rerun()
    
    # Display selected items
    selected_items = st.session_state[session_key]
    selected_names = [df.loc[df[id_col] == item_id, name_col].iloc[0] for item_id in selected_items]
    st.write(f"{label}: " + ", ".join(selected_names))
    
    return selected_items

def filter_df(role_items, race_items, special_items):
    df = joined['FMoves']

    # ---- Roles ----
    role_search = [i.strip() for i in role_items if i.strip()]
    role_masks = []
    for item in role_search:
        mask = df['roles'].fillna('').str.split(',').apply(lambda x: item in [s.strip() for s in x])
        role_masks.append(mask)

    # ---- Races ----
    race_search = [i.strip() for i in race_items if i.strip()]
    race_masks = []

    if "All" in race_search:
        race_masks.append(df['races'].fillna('') != '')  # keep all non-empty races
        race_search = [i for i in race_search if i != "All"]

    for item in race_search:
        mask = df['races'].fillna('').str.split(',').apply(lambda x: item in [s.strip() for s in x])
        race_masks.append(mask)

    # ---- Combine Roles OR Races ----
    all_masks = role_masks + race_masks
    if all_masks:
        combined_mask = pd.concat(all_masks, axis=1).any(axis=1)
        filtered_df = df[combined_mask]
    else:
        filtered_df = df.copy()

    # ---- Special (AND) ----
    special_search = [i.strip() for i in special_items.split(',') if i.strip()]
    for item in special_search:
        mask = filtered_df['special'].fillna('').str.split(',').apply(lambda x: item in [s.strip() for s in x])
        filtered_df = filtered_df[mask]

    return filtered_df.reset_index(drop=True)

# --- Streamlit Tabs ---
tab1, tab2 = st.tabs(["Moves", "Races & Roles"])

with tab1:
    st.write("#### Moves")

    df_roles = joined["Roles"][["ID", "name"]].astype(str)
    
    # Initialize show_races state if not exists
    if "show_races_state" not in st.session_state:
        st.session_state.show_races_state = False
    
    # Use modular function for roles selection
    roles_selected = render_selection_buttons(df_roles, "ID", "name", "selected_roles", "Roles")

    # Races & Special row
    col1, col2 = st.columns([1,1])
    with col1:
        show_races = st.toggle("Show Races", 
                                   value=st.session_state.show_races_state,
                                   key="show_races")
        # Update session state when toggle changes
        st.session_state.show_races_state = show_races
        races_items = ["All"] if show_races else []
    with col2:
        special_str = st.text_input("Special (comma-separated)", "")

    # Auto-run filter
    result = filter_df(roles_selected, races_items, special_str)
    # st.write(f"### Results")
    st.dataframe(result, use_container_width=True, height=min(38+len(result) * 35, 20000))

with tab2:
    st.write("#### Races")
    st.dataframe(joined['Races'], use_container_width=True, height=min(38+len(joined['Races']) * 35, 20000))  # unrestricted height

    st.write("#### Roles")
    
    # Add race selection buttons for filtering roles table
    df_races = joined["Races"][["ID", "name"]].astype(str)
    selected_race_ids = render_selection_buttons(df_races, "ID", "name", "selected_races_for_roles", "Races Selected", buttons_per_row=12)
    
    # Filter roles table based on selected races
    df_roles_display = joined['Roles'].copy()
    if selected_race_ids:
        # Filter roles that contain any of the selected races
        mask = df_roles_display['races'].fillna('').str.split(',').apply(
            lambda x: any(race_id.strip() in [s.strip() for s in x] for race_id in selected_race_ids+['any'])
        )
        df_roles_display = df_roles_display[mask]
    
    st.dataframe(df_roles_display, use_container_width=True, height=min(38+len(df_roles_display) * 35, 20000))
