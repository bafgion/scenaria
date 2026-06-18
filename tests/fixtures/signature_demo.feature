Функционал: UI сценарий
Сценарий: signature_demo
	Допустим открыт "file:///signature_demo.html"
	И жду появления "canvas#signature-canvas"
	И рисую подпись в "canvas#signature-canvas"
	И нажимаю "button#next-btn"
	Тогда вижу "#success.visible"
	И закрываю браузер
