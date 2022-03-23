import pandas as pd
import streamlit as st
import numpy as np
from PIL import Image
import base64
import plotly.express as px

st.set_page_config(layout='wide', page_title='Prepaid Multisim Subs Detection')

# ----- Load Data -----

@st.cache
def load_activations():
	df = pd.read_csv('202202.csv', parse_dates=['offer_start_date', 'offer_end_date', 'time_id'])
	df.discounted_price = pd.to_numeric(df.discounted_price, downcast='float', errors='coerce')
	df.main_balance_charge = pd.to_numeric(df.main_balance_charge, downcast='float', errors='coerce')
	df.opnumber = pd.to_numeric(df.opnumber, downcast='float', errors='coerce')
	df.final_charge = pd.to_numeric(df.final_charge, downcast='float', errors='coerce')
	return df

df = load_activations()

@st.cache
def load_broadcast_base():
	df = pd.read_csv('202202_bulk.csv', sep=',')
	df = df[df.control==0]
	df.rename({'msisdn':'telephone_number'}, axis=1, inplace=True)
	df['offer'] = df["offer"].str.cat(df.channel, sep ="_")
	df = df[['telephone_number', 'offer']]
	return df

broadcast_base = load_broadcast_base()


# ----- Sidebar -----

# Inser Logo image
image = Image.open('Azercell-Logo.png')
st.sidebar.image(image)

# Campaign selection
st.sidebar.subheader('Campaign selection')
campaign_list = df.offer.unique()
checkbox = st.sidebar.checkbox('All campaigns', value=True)
selected_campaigns = st.sidebar.multiselect('Select Campaign(s)', campaign_list, disabled=True if checkbox is True else False)

st.sidebar.write('---')

# Refresh button
st.sidebar.info('''Last data fetch was on: \n
**2022-03-23 9:53**''')
refresh = st.sidebar.button('🔄 Refresh')


# ----- Main Page -----

st.header('Prepaid Multisim Subs Detection')
st.markdown(f'**Campaign Period:** {df.offer_start_date.iloc[0].strftime("%Y-%m-%d")} - {df.offer_end_date.iloc[0].strftime("%Y-%m-%d")}')

# Filtering dataframes by checkbox condition
df = df[df.offer.isin(df.offer.unique() if checkbox is True else selected_campaigns)]
broadcast_base = broadcast_base[broadcast_base.offer.isin(broadcast_base.offer.unique() if checkbox is True else selected_campaigns)]

#Summary Figures
def get_summary_figures(df, bulk):
	broadcasted = len(bulk)
	responders = len(df)
	try:
		rate = round(responders / broadcasted * 100, 2)
	except:
		rate = 0
	return broadcasted, responders, rate

col1, col2, col3 = st.columns(3)
broadcasted, responders, rate = get_summary_figures(df, broadcast_base)
col1.markdown(f'<h1 style="color:#FF4B4B;font-size:24px;">{"📤 Broadcasted"}</h1>', unsafe_allow_html=True)
col1.markdown(f"**{broadcasted:,}**")
col2.markdown(f'<h1 style="color:#FF4B4B;font-size:24px;">{"✅ Responders"}</h1>', unsafe_allow_html=True)
col2.markdown(f'**{responders:,}**')
col3.markdown(f'<h1 style="color:#FF4B4B;font-size:24px;">{"📈 Response Rate"}</h1>', unsafe_allow_html=True)
col3.markdown(f'**{rate}%**')

# Total Activation Count by Date Plot
def plot_activations_by_date(df):
	df = df.groupby('time_id', as_index=False).agg(activations = ('telephone_number', 'count'))
	fig = px.bar(
		df, 
		x='time_id', 
		y='activations', 
		text_auto='.2s',
		labels={'time_id': 'Day', 'activations': 'Activation Count'},
		height=350
		)
	fig.update_traces(
	    hovertemplate="<br>".join([
	        "<b>%{x}</b>",
	        "Activations: %{y:,}"]))
	fig.update_layout(title_text='Responders Count by Date', title_x=0.5)
	return fig

st.subheader('Total Activations Count by Date')

fig = plot_activations_by_date(df)
st.plotly_chart(fig, use_container_width=True)

# Campaign Details
def plot_activation_count_by_campaign(df, bulk):
	df = df.groupby('offer', as_index=False).agg(activations = ('telephone_number', 'count'))
	bulk = bulk.groupby('offer', as_index=False).agg(broadcasted = ('telephone_number', 'count'))
	df = df.merge(bulk, on='offer')
	fig = px.bar(
		df, 
		x='offer', 
		y='activations', 
		custom_data=['broadcasted'],
		text_auto='.2s',
		labels={'offer': 'Campaign Name', 'activations': 'Activation Count'},
		height=550
		)
	fig.update_traces(
		    hovertemplate="<br>".join([
		        "<b>%{x}</b><br>",
		        "Activations: %{y:,}",
		        "Broadcasted: %{customdata[0]:,}"]))
	fig.update_layout(title_text='Responders Count', title_x=0.5)
	return fig

def plot_activation_share_by_campaign(df, bulk):
	df = df.groupby('offer').agg(activations = ('telephone_number', 'count'))
	bulk = bulk.groupby('offer').agg(activations = ('telephone_number', 'count'))
	df = (df / bulk).round(4)
	df = df.reset_index()
	df = df.rename({'activations':'response_rate'}, axis=1)
	fig = px.bar(
		df, 
		x='offer', 
		y='response_rate', 
		text_auto='.2%',
		labels={'offer': 'Campaign Name', 'response_rate': 'Response Rate'},
		height=550
		)
	fig.update_traces(
		    hovertemplate="<br>".join([
		        "<b>%{x}</b><br>",
		        "Response Rate: %{y:.2%}"]))
	fig.update_traces(textangle=0)
	fig.update_layout(title_text='Response Rate', title_x=0.5)
	fig.update_layout(yaxis_tickformat='.2%') 
	return fig

st.subheader('Campaign Details')
col1, col2 = st.columns(2)

fig = plot_activation_count_by_campaign(df, broadcast_base)
col1.plotly_chart(fig, use_container_width=True)

fig = plot_activation_share_by_campaign(df, broadcast_base)
col2.plotly_chart(fig, use_container_width=True)

# Print Responders Dataframe with Download option
st.subheader('Get Raw Data')
@st.cache
def convert_df(df):
	# IMPORTANT: Cache the conversion to prevent computation on every rerun
	return df.to_csv(index=False).encode('utf-8')

with st.expander('Responders DataFrame'):
	st.dataframe(df)
	st.download_button(label='Download CSV File', data=convert_df(df), file_name='responders.csv')