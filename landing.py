import streamlit as st

st.set_page_config(page_title="A.R.I.A. - Autonomous Revenue & Intelligence Agent", page_icon="", layout="wide")

# Custom CSS for landing page
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    .hero-section { 
        background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
        padding: 80px 0;
        border-radius: 0;
    }
    .hero-title { 
        font-size: 56px; 
        font-weight: 800; 
        color: #0F172A; 
        line-height: 1.1;
        margin-bottom: 24px;
    }
    .hero-subtitle { 
        font-size: 20px; 
        color: #64748B; 
        line-height: 1.6;
        margin-bottom: 40px;
    }
    .cta-button {
        background: #16A34A;
        color: white;
        padding: 16px 32px;
        border-radius: 12px;
        font-size: 18px;
        font-weight: 700;
        border: none;
        cursor: pointer;
        transition: all 0.2s;
    }
    .cta-button:hover {
        background: #15803D;
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(22, 163, 74, 0.3);
    }
    .feature-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    }
    .feature-icon {
        font-size: 48px;
        margin-bottom: 16px;
    }
    .metric-card {
        background: #F8FAFC;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
    }
    .metric-value {
        font-size: 36px;
        font-weight: 700;
        color: #16A34A;
    }
    .metric-label {
        font-size: 14px;
        color: #64748B;
        margin-top: 8px;
    }
    .pricing-card {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 16px;
        padding: 40px;
        text-align: center;
    }
    .pricing-card.featured {
        border-color: #16A34A;
        box-shadow: 0 10px 40px rgba(22, 163, 74, 0.15);
    }
    .price-amount {
        font-size: 48px;
        font-weight: 800;
        color: #0F172A;
    }
    .badge {
        background: #16A34A;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 16px;
    }
    @media (max-width: 768px) {
        .hero-title { font-size: 36px; }
        .hero-subtitle { font-size: 16px; }
    }
</style>
""", unsafe_allow_html=True)

# Navigation
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("<div style='display:flex; align-items:center; gap:12px; padding:20px 0;'><div style='font-size:32px;'>🔥</div><div><div style='font-size:24px; font-weight:800; color:#0F172A;'>A.R.I.A</div><div style='font-size:10px; color:#16A34A; font-weight:700; letter-spacing:1px;'>COMMAND CENTER</div></div></div>", unsafe_allow_html=True)
with col2:
    if st.button("Login →", use_container_width=True):
        st.switch_page("app.py")

st.markdown("---")

# Hero Section
st.markdown("""
<div class="hero-section">
    <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
        <div style="display: inline-block; background: #F0FDF4; color: #166534; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; margin-bottom: 24px;">
            🚀 Built for Hospitality & FMCG
        </div>
        <h1 class="hero-title">
            While you slept, A.R.I.A. found<br>
            <span style="color: #16A34A;">12 leads</span>, replied to<br>
            <span style="color: #16A34A;">4 reviews</span>, and drafted<br>
            <span style="color: #16A34A;">2 vendor emails</span>
        </h1>
        <p class="hero-subtitle">
            Six autonomous AI agents work the parts of your business that don't need your judgment,<br>
            and hand you the parts that do — one tap, on your phone.
        </p>
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
            <a href="app.py" style="text-decoration: none;">
                <button class="cta-button">Start 14-Day Free Trial →</button>
            </a>
            <button style="background: transparent; color: #0F172A; padding: 16px 32px; border-radius: 12px; font-size: 18px; font-weight: 600; border: 2px solid #E2E8F0; cursor: pointer;">Watch Demo</button>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Live Demo Preview
st.markdown("""
<div style="max-width: 1200px; margin: 60px auto; padding: 0 20px;">
    <h2 style="text-align: center; font-size: 36px; margin-bottom: 40px; color: #0F172A;">See A.R.I.A. in Action</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px;">
        <div class="metric-card">
            <div class="metric-value">340</div>
            <div class="metric-label">Businesses scanned/month</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">92%</div>
            <div class="metric-label">Valid email rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">4.8★</div>
            <div class="metric-label">Avg review response rating</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">₹18k</div>
            <div class="metric-label">Avg monthly savings</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Features Section
st.markdown("""
<div style="max-width: 1200px; margin: 80px auto; padding: 0 20px;">
    <h2 style="text-align: center; font-size: 36px; margin-bottom: 16px; color: #0F172A;">6 AI Agents Working for You</h2>
    <p style="text-align: center; font-size: 18px; color: #64748B; margin-bottom: 60px;">Autonomous tools that handle your business operations</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 24px;">
        <div class="feature-card">
            <div class="feature-icon"></div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">Lead Finder</h3>
            <p style="color: #64748B; line-height: 1.6;">Scans directories and maps for real businesses in your target area, verifies their emails, and builds a contact list you can act on.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">✉️</div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">Response Writer</h3>
            <p style="color: #64748B; line-height: 1.6;">Turns a new lead into a formatted property profile and a ready-to-send reply, matched to how your business actually talks.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">⭐</div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">Review Management</h3>
            <p style="color: #64748B; line-height: 1.6;">Reads every new review and drafts a reply in minutes — empathetic where it should be, on-brand always, never generic.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">🎨</div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">Content Studio</h3>
            <p style="color: #64748B; line-height: 1.6;">Feed it one photo, video, or post. It plans and drafts a full week of captions, stories, and follow-ups around it.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">🤝</div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">Negotiator</h3>
            <p style="color: #64748B; line-height: 1.6;">Compares your costs against market rates and drafts the negotiation email — the ask, the numbers, and the tone.</p>
        </div>
        
        <div class="feature-card">
            <div class="feature-icon">📱</div>
            <h3 style="font-size: 24px; margin-bottom: 12px; color: #0F172A;">WhatsApp Studio</h3>
            <p style="color: #64748B; line-height: 1.6;">Create engaging WhatsApp broadcasts with emojis and CTAs for your customer list. Turn one message into customer engagement.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Pricing Section
st.markdown("""
<div style="max-width: 1200px; margin: 100px auto; padding: 0 20px;">
    <h2 style="text-align: center; font-size: 36px; margin-bottom: 16px; color: #0F172A;">Simple, Transparent Pricing</h2>
    <p style="text-align: center; font-size: 18px; color: #64748B; margin-bottom: 60px;">No hidden fees. Cancel anytime.</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 32px; max-width: 800px; margin: 0 auto;">
        <div class="pricing-card featured">
            <div class="badge">MOST POPULAR</div>
            <h3 style="font-size: 24px; margin-bottom: 8px; color: #0F172A;">Professional</h3>
            <div style="color: #64748B; margin-bottom: 24px;">For growing businesses</div>
            <div class="price-amount">₹2,999<span style="font-size: 18px; color: #64748B; font-weight: 400;">/month</span></div>
            <ul style="text-align: left; margin: 32px 0; padding-left: 20px; color: #374151;">
                <li style="margin-bottom: 12px;">✅ All 6 AI modules</li>
                <li style="margin-bottom: 12px;">✅ 500 AI generations/month</li>
                <li style="margin-bottom: 12px;">✅ Email support</li>
                <li style="margin-bottom: 12px;">✅ Telegram integration</li>
                <li style="margin-bottom: 12px;">✅ 14-day free trial</li>
            </ul>
            <a href="app.py" style="text-decoration: none;">
                <button class="cta-button" style="width: 100%;">Start Free Trial</button>
            </a>
        </div>
        
        <div class="pricing-card">
            <h3 style="font-size: 24px; margin-bottom: 8px; color: #0F172A;">Enterprise</h3>
            <div style="color: #64748B; margin-bottom: 24px;">For agencies & teams</div>
            <div class="price-amount">₹4,999<span style="font-size: 18px; color: #64748B; font-weight: 400;">/month</span></div>
            <ul style="text-align: left; margin: 32px 0; padding-left: 20px; color: #374151;">
                <li style="margin-bottom: 12px;">✅ Everything in Professional</li>
                <li style="margin-bottom: 12px;">✅ Unlimited generations</li>
                <li style="margin-bottom: 12px;">✅ Priority support</li>
                <li style="margin-bottom: 12px;">✅ Team collaboration</li>
                <li style="margin-bottom: 12px;">✅ Custom integrations</li>
            </ul>
            <a href="app.py" style="text-decoration: none;">
                <button style="width: 100%; background: white; color: #0F172A; padding: 16px 32px; border-radius: 12px; font-size: 18px; font-weight: 700; border: 2px solid #E2E8F0; cursor: pointer;">Contact Sales</button>
            </a>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# CTA Section
st.markdown("""
<div style="background: linear-gradient(135deg, #16A34A 0%, #15803D 100%); padding: 80px 0; margin-top: 100px;">
    <div style="max-width: 800px; margin: 0 auto; text-align: center; padding: 0 20px;">
        <h2 style="font-size: 42px; color: white; margin-bottom: 24px;">Ready to automate your business?</h2>
        <p style="font-size: 20px; color: #F0FDF4; margin-bottom: 40px;">Join hundreds of businesses saving 15+ hours per week with A.R.I.A.</p>
        <a href="app.py" style="text-decoration: none;">
            <button style="background: white; color: #16A34A; padding: 20px 48px; border-radius: 12px; font-size: 20px; font-weight: 800; border: none; cursor: pointer; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">Start Your Free Trial →</button>
        </a>
        <p style="color: #F0FDF4; margin-top: 24px; font-size: 14px;">No credit card required • 14-day free trial • Cancel anytime</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="background: #0F172A; color: #94A3B8; padding: 40px 0; text-align: center;">
    <div style="max-width: 1200px; margin: 0 auto; padding: 0 20px;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 24px;">
            <div style="font-size: 32px;">🔥</div>
            <div>
                <div style="font-size: 24px; font-weight: 800; color: #F8FAFC;">A.R.I.A</div>
                <div style="font-size: 10px; color: #16A34A; font-weight: 700; letter-spacing: 1px;">COMMAND CENTER</div>
            </div>
        </div>
        <p style="margin-bottom: 24px;">Autonomous Revenue & Intelligence Agent</p>
        <div style="border-top: 1px solid #1E293B; padding-top: 24px; font-size: 14px;">
            © 2026 A.R.I.A. SaaS. All rights reserved. • Built for Indian businesses
        </div>
    </div>
</div>
""", unsafe_allow_html=True)