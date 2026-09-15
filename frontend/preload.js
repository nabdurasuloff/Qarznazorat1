const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('qarzNazorat', {
    getBackendPort: () => ipcRenderer.invoke('backend-port'),
    tarmoqSozlamasiniOlish: () => ipcRenderer.invoke('tarmoq-sozlamasi-olish'),
    tarmoqSozlamasiniSaqlash: (server_ip) => ipcRenderer.invoke('tarmoq-sozlamasi-saqlash', server_ip),
    dasturniQaytaIshgaTushirish: () => ipcRenderer.invoke('dasturni-qayta-ishga-tushirish'),
});
