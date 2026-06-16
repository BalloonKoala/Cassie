/**
 * Cassie connection defaults.
 * On Firebase Hosting the brain server must be a public WSS URL (Cloud Run or home tunnel).
 * Set brainServer after deploying server, or pass ?server=wss://... on the Pi kiosk URL.
 */
window.CASSIE_DEFAULTS = {
  brainServer: "",
  device: "pi-home",
  token: "change-me"
};

window.CASSIE_HOSTING = {
  site: "https://hobbifinder.web.app",
  alt: "https://hobbifinder.firebaseapp.com"
};
