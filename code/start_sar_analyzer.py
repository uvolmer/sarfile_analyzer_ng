#!/usr/bin/python3

import streamlit as st
from streamlit_option_menu import option_menu
import os
import time
import datetime
import sql_stuff
from sqlite2_polars import get_table_df
from config import Config
import mng_sar
import analyze_pl
import db_mng
import helpers_pl as helpers
import todo
import redis_mng
import help
import info
import self_service
import handle_user_status

st.set_page_config(
    page_title="Happy SAR Analyzer",
    layout='wide',
    page_icon="wiki_pictures/kisspng-penguin-download-ico-icon-penguin-5a702cc04e5fc1.8432243315173009283211.png",
)

start_time = time.perf_counter()

def local_css(file_name: str):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def remote_css(url: str):
    st.markdown(f'<link href="{url}" rel="stylesheet">',
                unsafe_allow_html=True)

def icon(icon_name: str):
    st.markdown(
        f'<i class="material-icons">{icon_name}</i>', unsafe_allow_html=True)

cur_dir = os.path.dirname(os.path.realpath(__file__))
local_css(f"{cur_dir}/style.css")
remote_css('https://fonts.googleapis.com/icon?family=Material+Icons')

user_status_df = handle_user_status.load_df_from_file()[0]

def start():
    """Sar analyzeer App"""
    st.title = "SAR Analyzer"
    with st.sidebar:
        choice = option_menu("Menu", ["Login", "Signup", "Help", "Logout"],
                             icons=['arrow-right-circle-fill',
                                    'pencil', 'question-square', 'arrow-left-circle-fill'],
                             menu_icon="app-indicator", default_index=0,
                             styles={
            "container": {"padding": "5!important", "background-color": "#91cfec",},
            "icon": {"color": "orange", "font-size": "25px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee",
                         "background-color": "#91cfe"},
            "nav-link-selected": {"background-color": "#1a7c78"},
        }
        )
    
        
    cached_obj = "sql_connection_obj"
    if not st.session_state.get(cached_obj, []):
        sql_stuff.create_tables()
        helpers.set_state_key(cached_obj, value=True, 
            change_key='sql_connection')
    config_c = helpers.configuration({})

    if choice == "Help":
        help.help()
    if choice == 'Logout':
        if st.session_state.get('username'):
            st.session_state.pop('username')
    elif choice == "Login":
        ph_username = st.sidebar.empty()
        ph_password = st.sidebar.empty()
        ph_login = st.sidebar.empty()
        username = ph_username.text_input("Username")
        password = ph_password.text_input("Password", type='password')
        if st.session_state.get('username', None) == username:
            ph_username.empty()
            ph_password.empty()
            main_body(username, config_c)
        else:
            if ph_login.button("Login"):
                now = datetime.datetime.now()
                if sql_stuff.login_user(username, password):
                    st.session_state.username = username
                    ph_username.empty()
                    ph_password.empty()
                    ph_login.empty()
                    handle_user_status.add_record(username, now, True)
                    main_body(username, config_c)
                else:
                    st.warning("You don't exist or your password does not match")
                    handle_user_status.add_record(username, now, False)
            else:
                st.markdown("## Please login to use this app")
    elif (choice) == "Signup":
        st.subheader("Create an Account")
        col1, _ = st.columns([0.2, 0.8])
        new_user = col1.text_input("Username")
        new_password = col1.text_input("Password", type='password')
        if st.button("Signup"):
            if sql_stuff.add_userdata(new_user,new_password):
                st.success("You have successfully created an valid Account")
                st.info("Goto Login Menu to login")
            else:
                st.warning(f'User {new_user} already exists')

def main_body(username: str, config_c: helpers.configuration) :
    upload_dir = f'{Config.upload_dir}/{username}'
    os.system(f'mkdir -p {upload_dir}')
    sar_files = os.listdir(upload_dir)
    st.sidebar.success(f"Logged in as {username}")
    
    col1, col2 = st.columns(2)
    config_c.update_conf({'username': username, 'upload_dir': upload_dir,
        'sar_files':sar_files, 'cols':[col1, col2]})
    if sql_stuff.get_role(username) == "admin":
        top_choice = option_menu("Tasks",  ["Analyze Data", "Manage Sar Files", "DB Management",
            "Redis Management", "TODO", "Self Service", "User Management", "Info"],
                 icons=['calculator', 'receipt', 'bank', 'hdd-stack','clipboard','person', 
                    'people', 'info-circle', ],
                 menu_icon="yin-yang", default_index=0, orientation="horizontal",
            styles={
                "container": {"padding": "4!important", "background-color": "#91cfec", 
                    "margin-top" : 0,
                    },
                "icon": {"color": "orange", "font-size": "12px"},
                "nav-link": {"font-size": "12px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#1a7c78"},
            }
        )
    else:
        top_choice = option_menu("Tasks",  ["Analyze Data", "Manage Sar Files",
            "Self Service", "Info"],
                 icons=['calculator', 'receipt', 'person', 'info-circle', ],
                 menu_icon="yin-yang", default_index=0, orientation="horizontal",
            styles={
                "container": {"padding": "4!important", "background-color": "#91cfec", "margin-top" : 0},
                "icon": {"color": "orange", "font-size": "12px"},
                "nav-link": {"font-size": "12px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
                "nav-link-selected": {"background-color": "#1a7c78"},
            }
        )
    if top_choice == "Manage Sar Files":
        mng_sar.file_mng(upload_dir, username)
    elif top_choice == "Analyze Data":
        analyze_pl.analyze(config_c, username)
    elif top_choice == "DB Management":
        headings_df = get_table_df('headingstable')
        metrics_df = get_table_df('metric')
        db_mng.db_mgmt(headings_df, metrics_df)
    elif top_choice == "TODO":
        todo.todo()
    elif top_choice == "Redis Management":
        try:
            redis_mng.redis_tasks(col2)
        except Exception as e:
            st.warning(f"Exception: {e} recieved")
    elif top_choice == "Info":
        info.info()
        info.usage()
        info.code()
    elif top_choice == 'Self Service':
        self_service.self_service(username)
    elif top_choice == 'User Management':
        self_service.admin_service() 

if __name__ == "__main__":
    start()
    end = time.perf_counter()
    st.write(f'process_time: {round(end-start_time, 4)}')
