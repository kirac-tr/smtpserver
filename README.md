# smtpserver
DVR, NVR veya IP Kamera cihazlarınızın mail özelliğini kullanarak çalışır.
Oluşturulan SMTP server üzerine yönlendirdiğinizde, belirtilen cihazlarda gerekli hareket algılama, alarm gibi özellikleri aktif ettiğinizde sunucunuza resim eklenmiş şekilde gelen mailin içerindeki resmi alır ve deepstack server' a gönderir. Deepstack server person,car,cat,dog vs. gibi nesne algıladığında nesne cv2 modülü ile çizilir ve telegram botunuza veya botu eklemiş olduğunuz gruba mesaj olarak gönderir. 
Geliştirmeye açıktır. Kullanılan yerlerde kirac-tr kullanılması zorunludur.
docker-compose.yaml içeriğini kendinize göre düzenleyin, açıklamaları dikkatli okuyun.
