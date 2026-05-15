APP_CSS = r"""
<style>
:root {
  --pm-navy: #102a43;
  --pm-blue: #1f5f99;
  --pm-pale: #f3f7fb;
  --pm-border: #d8e3ee;
  --pm-text: #243b53;
  --pm-muted: #627d98;
}
.block-container {max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem;}
[data-testid="stSidebar"] {border-right: 1px solid var(--pm-border);}
.pm-hero {padding: 1.25rem 1.4rem 1.15rem; border: 1px solid var(--pm-border); border-radius: 16px; background: linear-gradient(135deg,#f8fbff 0%,#eef5fb 100%); margin-bottom: .72rem;}
.pm-kicker {font-size:.76rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--pm-blue); margin-bottom:.3rem;}
.pm-title {font-size:2.25rem; line-height:1.08; font-weight:780; color:var(--pm-navy); margin:0;}
.pm-subtitle {font-size:1.05rem; line-height:1.5; color:var(--pm-text); margin:.45rem 0 0; max-width:900px;}
.pm-author-card {display:flex; align-items:center; gap:1rem; padding:.78rem 1rem; margin:0 0 .9rem; background:#fff; border:1px solid var(--pm-border); border-left:4px solid var(--pm-blue); border-radius:12px; box-shadow:0 1px 2px rgba(16,42,67,.035);}
.pm-author-label {flex-shrink:0; font-size:.72rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--pm-muted);}
.pm-author-details {display:flex; align-items:center; flex-wrap:wrap; gap:.35rem; font-size:.88rem; color:var(--pm-text);}
.pm-author-details strong {color:var(--pm-navy);}
.pm-author-details a {color:var(--pm-blue); text-decoration:none; font-weight:600;}
.pm-author-details a:hover {text-decoration:underline;}
.pm-author-divider {color:#9fb3c8;}
.pm-section-title {font-size:1.25rem; font-weight:720; color:var(--pm-navy); margin:.55rem 0 .15rem;}
.pm-section-copy {font-size:.92rem; color:var(--pm-muted); margin-bottom:.65rem;}
.pm-usage-card {display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.42rem .7rem .34rem; margin:.42rem 0 0; border:1px solid var(--pm-border); border-bottom:0; border-radius:9px 9px 0 0; background:#fbfdff;}
.pm-usage-main {display:flex; align-items:baseline; flex-wrap:wrap; gap:.45rem;}
.pm-usage-label {font-size:.62rem; font-weight:700; letter-spacing:.055em; text-transform:uppercase; color:var(--pm-muted);}
.pm-usage-value {font-size:.8rem; font-weight:700; color:var(--pm-navy);}
.pm-usage-remaining {font-size:.72rem; font-weight:700; color:var(--pm-blue); white-space:nowrap;}
.pm-usage-track {height:3px; margin:0 0 .52rem; overflow:hidden; border:1px solid var(--pm-border); border-top:0; border-radius:0 0 9px 9px; background:#edf3f8;}
.pm-usage-fill {height:100%; background:var(--pm-blue); transition:width .2s ease;}
.pm-card {border:1px solid var(--pm-border); border-radius:14px; padding:1rem 1.05rem; background:#fff; height:100%; box-shadow:0 1px 2px rgba(16,42,67,.035);}
.pm-card-title {font-weight:720; color:var(--pm-navy); margin-bottom:.28rem;}
.pm-meta {font-size:.8rem; color:var(--pm-muted);}
.pm-verdict {display:inline-block; padding:.42rem .72rem; border-radius:10px; border:1px solid var(--pm-border); background:var(--pm-pale); color:var(--pm-navy); font-weight:750; text-transform:capitalize; margin-bottom:.7rem;}
.pm-idea {border-left:4px solid var(--pm-blue); border-top:1px solid var(--pm-border); border-right:1px solid var(--pm-border); border-bottom:1px solid var(--pm-border); border-radius:12px; padding:1rem 1.05rem; background:#fff; margin:.75rem 0;}
.pm-field-label {font-size:.77rem; text-transform:uppercase; letter-spacing:.06em; color:var(--pm-muted); font-weight:700; margin-top:.65rem;}
.pm-field-value {font-size:.94rem; line-height:1.52; color:var(--pm-text);}
.pm-citation {font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.79rem; color:var(--pm-blue);}
.pm-footer {margin-top:2.5rem; padding-top:1rem; border-top:1px solid var(--pm-border); color:var(--pm-muted); font-size:.82rem; text-align:center;}
.stButton > button[kind="primary"] {border-radius:10px; font-weight:700;}
[data-testid="stFileUploader"] {border:1px dashed #9fb7cc; border-radius:14px; padding:.4rem;}
@media (max-width: 640px) {
  .pm-author-card {align-items:flex-start; flex-direction:column; gap:.35rem;}
  .pm-author-details {line-height:1.5;}
}
</style>
"""
