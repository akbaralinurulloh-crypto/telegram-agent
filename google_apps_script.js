/**
 * =================================================================
 * TELEGRAM AI AGENT — GOOGLE SHEETS AVTOMATIK QABUL QILUVCHI KOD
 * =================================================================
 * 
 * QANDAY O'RNATILADI (1 daqiqa):
 * 1. Google Drive da yangi Google Sheets (Jadval) oching.
 * 2. Tepada 'Kengaytmalar' (Extensions) -> 'Apps Script' bo'limiga kiring.
 * 3. U yerda turgan kodni o'chirib, ushbu kodni to'liq joylashtiring (Paste).
 * 4. Tepada 'Deploy' (Joylashtirish) -> 'New deployment' tugmasini bosing.
 * 5. 'Select type' (G'ildirakcha belgisi) -> 'Web app' ni tanlang.
 * 6. 'Who has access' (Kimda ruxsat bor) joyiga: 'Anyone' (Hamma) qilib belgilang.
 * 7. 'Deploy' tugmasini bosing va berilgan 'Web app URL' manzilini nusxalab oling.
 * 8. O'sha URL manzilni .env fayliga GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/... qilib qo'ying!
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Agar sarlavhalar (Header) bo'lmasa, 1-qatorga avtomatik sarlavhalar yozish
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Sana va Vaqt",
        "Manba Kanal",
        "Xabar ID",
        "Format",
        "Kategoriya",
        "Final Ball (0-100)",
        "Holat",
        "Qaror / Sabab",
        "Yaratilgan Post Matni"
      ]);
      sheet.getRange(1, 1, 1, 9).setFontWeight("bold").setBackground("#1e293b").setFontColor("#ffffff");
    }
    
    var data = JSON.parse(e.postData.contents);
    
    // Yangi ma'lumotni jadvalga qo'shish
    sheet.appendRow([
      data.timestamp || new Date(),
      data.source_channel || "",
      data.source_message_id || "",
      data.media_type || "",
      data.category || "",
      data.final_score || 0,
      data.status || "",
      data.reason || "",
      data.caption || ""
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({ "result": "success" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ "result": "error", "error": error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
