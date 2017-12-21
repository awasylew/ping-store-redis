## TODO wdrażanie REDIS
# usuwanie wszystkich pingów na pierwszej stronie
# dodanie usuwania pingów w wersji Redis
# test długotrwały probe-chmura
# pełny przegląd co zrobić z parametrami zapytań SQL
# testy dla rozbudowanego get_pings_redis
# deployment na AWS
# parametry ze środowiska
# zachowania przy braku parametrów obowiązkowych
# zautomatyzowana budowa środowiska
# wszystkie wcześniejsze testy SQL działają na Redis
# implementacja metod delete
# paczkowanie/transakcje
# wyniki w agregatach minutes???

## TODO merge REDIS + SQL
# porządkowanie zdublowanych metod SQL na styku z Flask (pseudo, ...)
# struktury danych PingResult i sensowne+jednolite przekazywanie parametrów/wyników
# podejście do time vs day/hour/minute/second
# SQL przechodzi wszystkie testy Redis
# łączenie lub porządkowanie testów
# uniezależnianie testów od magazynu
# parametry do testowania ze środowiska
# jeden skrypt testowy na cały SQL+Redis
# przegląd i ocena pokrycia testami
# łączenie index
# index/makedb tylko dla SQL? automatyczne rozpoznanie?
# testowanie naprzemienne ping-show, może coś zautomatyzować?
# posprzątać templates w show pod kątem urli vs Lambda/dev
