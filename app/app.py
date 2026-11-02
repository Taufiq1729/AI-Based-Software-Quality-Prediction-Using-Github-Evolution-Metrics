import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import joblib
import shap
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from src.data.feature_extractor import FEATURE_COLUMNS

# Must be the first Streamlit command
st.set_page_config(page_title="AI Software Quality Prediction", page_icon="🔮", layout="wide", initial_sidebar_state="collapsed")

# --- PREMIUM GLASSMORPHISM DARK THEME CSS ---
st.markdown("""
<style>
    /* Global background with smooth dark gradient */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide top bar */
    header {visibility: hidden;}
    
    /* Typography improvements */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    
    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        margin-bottom: 24px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    
    /* Metrics Styling inside Cards */
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #a78bfa, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }
    .metric-title {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.05);
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #cbd5e1;
        border: none;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(139, 92, 246, 0.1) !important;
        color: #a78bfa !important;
        border-bottom: 2px solid #a78bfa !important;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #8b5cf6 0%, #d946ef 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(217, 70, 239, 0.4);
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.05) !important;
        border-radius: 8px !important;
        color: #f8fafc !important;
    }
    
    /* Sliders */
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #8b5cf6 0%, #d946ef 100%);
    }
    
</style>
""", unsafe_allow_html=True)

# Remove caching so it always reads the latest JSON
def load_data():
    results_dir = "data/results"
    
    metrics_path = os.path.join(results_dir, "evaluation_metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
    else:
        metrics = None
        
    importance_path = os.path.join(
        results_dir,
        "logistic_regression_combined_feature_coefficients.csv",
    )
    if os.path.exists(importance_path):
        feature_importance = pd.read_csv(importance_path)
    else:
        feature_importance = None
        
    return metrics, feature_importance

# Title Area
st.markdown("""
<div style="text-align: center; padding: 40px 0;">
    <h1 style="font-size: 3.5rem; margin-bottom: 10px; background: linear-gradient(90deg, #8b5cf6, #d946ef); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🔮 SQAM Analytics Engine</h1>
    <p style="font-size: 1.2rem; color: #94a3b8;">AI-Based Software Quality Prediction Using GitHub Evolution Metrics</p>
</div>
""", unsafe_allow_html=True)

metrics, feature_importance = load_data()

tab1, tab2, tab3, tab4 = st.tabs([
    "📖 Project Overview", 
    "📊 RQ1 & RQ3: Model Performance", 
    "🔍 RQ2 & RQ4: Explainability", 
    "🛠️ Interactive Predictor"
])

with tab1:
    st.markdown("""
    <div class="glass-card">
        <h2>The Objective</h2>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #cbd5e1;">
        Estimating the quality risk of software components by combining <b>source-code metrics</b> with <b>Git evolution metrics</b> using machine-learning. This dashboard empowers testers and developers to prioritize code review and testing based on quantitative defect-proneness evidence.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="glass-card" style="height: 100%;">
            <h3 style="color: #a78bfa !important;">🧩 Static Code Metrics</h3>
            <p style="color: #94a3b8;">Derived directly from the source code structure.</p>
            <ul style="color: #cbd5e1; line-height: 1.8;">
                <li><b>LOC</b>: Lines of Code</li>
                <li><b>WMC</b>: Weighted Methods per Class</li>
                <li><b>DIT</b>: Depth of Inheritance Tree</li>
                <li><b>CBO</b>: Coupling Between Objects</li>
                <li><b>LCOM5</b>: Lack of Cohesion in Methods</li>
                <li><b>RFC</b>: Response For a Class</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="glass-card" style="height: 100%;">
            <h3 style="color: #ec4899 !important;">📈 Git Evolution Metrics</h3>
            <p style="color: #94a3b8;">Derived from the repository history over time.</p>
            <ul style="color: #cbd5e1; line-height: 1.8;">
                <li><b>Code Churn</b>: Lines added/deleted/modified. (Measures instability)</li>
                <li><b>Revision Count</b>: Number of historical commits. (Measures active evolution)</li>
                <li><b>Developer Count</b>: Distinct developers. (Measures ownership distribution)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    if metrics:
        models = list(metrics.keys())
        
        st.markdown("<div class='glass-card'><h2>Model Performance Comparison</h2><p>Evaluating how Evolution Metrics improve the baseline.</p></div>", unsafe_allow_html=True)
        
        selected_model = st.selectbox("Select Model", models, index=2)
        m_data = metrics[selected_model]
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"""
            <div class="glass-card" style="border-top: 4px solid #1f77b4;">
                <h3 style="text-align: center;">Static Metrics Only</h3>
                <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                    <div style="text-align: center;">
                        <div class="metric-title">ROC-AUC</div>
                        <div class="metric-value" style="background: #1f77b4; -webkit-background-clip: text;">{m_data['static']['ROC_AUC']:.3f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="metric-title">F1 Score</div>
                        <div class="metric-value" style="background: #1f77b4; -webkit-background-clip: text;">{m_data['static']['F1_Score']:.3f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_m2:
            st.markdown(f"""
            <div class="glass-card" style="border-top: 4px solid #d946ef;">
                <h3 style="text-align: center;">Static + Evolution</h3>
                <div style="display: flex; justify-content: space-around; margin-top: 20px;">
                    <div style="text-align: center;">
                        <div class="metric-title">ROC-AUC</div>
                        <div class="metric-value" style="background: #d946ef; -webkit-background-clip: text;">{m_data['combined']['ROC_AUC']:.3f}</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="metric-title">F1 Score</div>
                        <div class="metric-value" style="background: #d946ef; -webkit-background-clip: text;">{m_data['combined']['F1_Score']:.3f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        # ROC Curve Plotly
        if "ROC_Curve" in m_data["combined"]:
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(x=m_data["static"]["ROC_Curve"]["fpr"], y=m_data["static"]["ROC_Curve"]["tpr"],
                                         mode='lines', name=f'Static Only (AUC = {m_data["static"]["ROC_AUC"]:.3f})',
                                         line=dict(color='#1f77b4', width=3)))
            fig_roc.add_trace(go.Scatter(x=m_data["combined"]["ROC_Curve"]["fpr"], y=m_data["combined"]["ROC_Curve"]["tpr"],
                                         mode='lines', name=f'Static + Evolution (AUC = {m_data["combined"]["ROC_AUC"]:.3f})',
                                         line=dict(color='#d946ef', width=3)))
            fig_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', name='Random Guess', line=dict(color='rgba(255,255,255,0.2)', dash='dash')))
            
            fig_roc.update_layout(
                title='Receiver Operating Characteristic (ROC)',
                xaxis_title='False Positive Rate', yaxis_title='True Positive Rate',
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#cbd5e1'),
                legend=dict(yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)")
            )
            fig_roc.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            fig_roc.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.plotly_chart(fig_roc, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Evaluation metrics not found. Please run the ML pipeline.")

with tab3:
    if feature_importance is not None:
        st.markdown(
            "<div class='glass-card'><h2>Logistic Regression Combined Explainability</h2>"
            "<p>Signed coefficients describe model direction; absolute magnitudes are scale-dependent "
            "and are not causal contributions.</p></div>",
            unsafe_allow_html=True,
        )
        
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            top_coefficients = feature_importance.nlargest(10, "Absolute_Coefficient")
            fig_fi = px.bar(
                top_coefficients.sort_values("Absolute_Coefficient", ascending=True),
                x="Absolute_Coefficient",
                y="Feature",
                orientation="h",
                color="Signed_Coefficient",
                color_continuous_scale="RdBu",
                color_continuous_midpoint=0,
                hover_data={"Signed_Coefficient": ":.6g", "Absolute_Coefficient": ":.6g"},
            )
            fig_fi.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#cbd5e1'),
                title="Top 10 Logistic Regression Coefficient Magnitudes",
                xaxis_title="Absolute coefficient (not causal influence)",
                showlegend=False, margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig_fi, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<div class='glass-card' style='text-align: center; overflow: hidden;'>", unsafe_allow_html=True)
            st.markdown("### Logistic Regression Combined SHAP Summary")
            st.markdown(
                "<p style='color: #94a3b8; font-size: 0.9rem;'>"
                "Positive-class (defective = 1) contributions in log-odds space. "
                "Feature values are standardized; red = above the training mean, "
                "blue = below the training mean.</p>",
                unsafe_allow_html=True,
            )
            
            results_dir = "data/results"
            shap_values_path = os.path.join(
                results_dir,
                "logistic_regression_combined_shap_values.npy",
            )
            shap_sample_path = os.path.join(
                results_dir,
                "logistic_regression_combined_shap_X_sample.csv",
            )
            
            if os.path.exists(shap_values_path) and os.path.exists(shap_sample_path):
                shap_values = np.load(shap_values_path)
                X_sample = pd.read_csv(shap_sample_path)
                metadata_path = os.path.join(
                    results_dir,
                    "logistic_regression_combined_explanation_metadata.json",
                )
                if (
                    list(X_sample.columns) != FEATURE_COLUMNS
                    or shap_values.shape != X_sample.shape
                    or not os.path.exists(metadata_path)
                ):
                    st.error("Logistic Regression SHAP artifacts are incomplete or have an invalid feature schema.")
                else:
                    with open(metadata_path, "r", encoding="utf-8") as file:
                        explanation_metadata = json.load(file)
                    if (
                        explanation_metadata.get("model_file") != "LogisticRegression_combined.pkl"
                        or explanation_metadata.get("feature_columns") != FEATURE_COLUMNS
                        or explanation_metadata.get("positive_class") != 1
                    ):
                        st.error("SHAP metadata does not identify Logistic Regression Combined class 1.")
                    else:
                        plt.style.use('dark_background')
                        fig, ax = plt.subplots(figsize=(7, 5))
                        fig.patch.set_facecolor('none')
                        ax.set_facecolor('none')
                        shap.summary_plot(shap_values, X_sample, show=False, plot_size=(7, 5))
                        st.pyplot(fig)
            else:
                st.info("SHAP values not generated yet.")
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Feature importance data not found.")

with tab4:
    st.markdown(
        "<div class='glass-card'><h2>SQA Interactive Predictor</h2>"
        "<p>Explore an uncalibrated model score for a hypothetical Java component. "
        "Scores prioritize manual review; they do not confirm or rule out defects.</p></div>",
        unsafe_allow_html=True,
    )
    
    with st.container():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        c_stat, c_evo = st.columns(2)
        
        with c_stat:
            st.markdown("<h3 style='color: #a78bfa;'>📊 Static Metrics</h3>", unsafe_allow_html=True)
            loc = st.slider("Lines of Code (LOC)", 10, 2000, 150)
            wmc = st.slider("Complexity (WMC)", 1, 100, 10)
            cbo = st.slider("Coupling (CBO)", 0, 50, 5)
            rfc = st.slider("Response For Class (RFC)", 0, 100, 15)
            lcom = st.slider("Lack of Cohesion (LCOM5)", 0.0, 2.0, 0.5)
            dit = st.slider("Depth of Inheritance (DIT)", 1, 10, 2)
            
            with st.expander("Advanced OO Metrics"):
                c1, c2 = st.columns(2)
                noc = c1.number_input("NOC", 0)
                npa = c1.number_input("NPA", 0)
                npm = c2.number_input("NPM", 5)
                nle = c2.number_input("NLE", 1)
                cboi = c1.number_input("CBOI", 2)
                cd = c2.number_input("CD (Comment Density)", 0.1)

        with c_evo:
            st.markdown("<h3 style='color: #ec4899;'>📈 Evolution Metrics</h3>", unsafe_allow_html=True)
            churn = st.slider("Code Churn", 0, 5000, 100)
            revisions = st.slider("Revision Count", 1, 200, 10)
            devs = st.slider("Developer Count", 1, 50, 2)
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            predict_btn = st.button("🔍 ANALYZE COMPONENT RISK")

        st.markdown("</div>", unsafe_allow_html=True)

    if predict_btn:
        model_path = "src/models/saved/LogisticRegression_combined.pkl"
        scaler_path = "data/processed/scaler.pkl"
        medians_path = "data/processed/imputer_medians.json"
        
        if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(medians_path):
            try:
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                with open(medians_path, "r", encoding="utf-8") as medians_file:
                    medians = json.load(medians_file)
                
                input_data = {
                    'LOC': loc, 'WMC': wmc, 'DIT': dit, 'NOC': noc, 'RFC': rfc,
                    'LCOM5': lcom, 'CBO': cbo, 'NPA': npa, 'NPM': npm, 'NLE': nle,
                    'CBOI': cboi, 'CD': cd, 'code_churn': churn,
                    'revision_count': revisions, 'developer_count': devs
                }
                
                input_df = pd.DataFrame([input_data], columns=FEATURE_COLUMNS)
                input_df = input_df.fillna(medians)
                scaled_df = pd.DataFrame(
                    scaler.transform(input_df),
                    columns=FEATURE_COLUMNS,
                )
                positive_class_index = list(model.classes_).index(1)
                prob = model.predict_proba(scaled_df)[0][positive_class_index]
                pred = int(model.predict(scaled_df)[0])
                score_display = "<0.001" if 0 < prob < 0.001 else f"{prob:.3f}"
                
                if pred == 1:
                    bg_color = "rgba(239, 68, 68, 0.2)"
                    border_color = "#ef4444"
                    status = "⚠️ HIGH MODEL SCORE"
                    msg = "The score exceeds the configured review threshold. Consider manual review."
                else:
                    bg_color = "rgba(34, 197, 94, 0.2)"
                    border_color = "#22c55e"
                    status = "✅ LOWER MODEL SCORE"
                    msg = "The score is below the configured review threshold; this does not establish that the component is defect-free."
                    
                st.markdown(f"""
                <div class="glass-card" style="background: {bg_color}; border-color: {border_color}; text-align: center; margin-top: 20px;">
                    <h2 style="color: {border_color}; font-size: 2.5rem; margin-bottom: 10px;">{status}</h2>
                    <div style="font-size: 4rem; font-weight: 800; color: white; margin-bottom: 10px;">Model score (0–1): {score_display}</div>
                    <p style="font-size: 1.2rem; color: #cbd5e1;">{msg}</p>
                </div>
                """, unsafe_allow_html=True)
                        
            except Exception as e:
                st.error(f"Error making prediction: {e}")
        else:
            st.error("Logistic Regression Combined model, training scaler, or imputation medians were not found.")
