export default {
  async fetch(request, env, ctx) {
    // PENTING: Ganti URL di bawah ini dengan URL PythonAnywhere Anda nanti!
    // Contoh: "https://mesrini.pythonanywhere.com"
    const TARGET_URL = "https://jeffCode.pythonanywhere.com";
    
    const url = new URL(request.url);
    const target = new URL(TARGET_URL);
    
    // Ubah hostname dan protocol request agar mengarah ke PythonAnywhere
    url.hostname = target.hostname;
    url.protocol = target.protocol;
    
    // Buat request baru ke target PythonAnywhere
    const newRequest = new Request(url, request);
    
    // Teruskan request dan kembalikan responsnya ke pengguna
    return fetch(newRequest);
  }
}