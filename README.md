## TODO wdrażanie REDIS
# sortowanie wyników wg czasu - ale gdzie?
# dodanie usuwania pingów (metody DELETE)
# pełny przegląd co zrobić z parametrami zapytań SQL
# testy dla rozbudowanego get_pings_redis
# deployment na AWS
# parametry REDIS ze środowiska (częściowo zrobione z powodu Heroku)
# zachowania przy braku parametrów obowiązkowych
# zautomatyzowana budowa środowiska
# wszystkie wcześniejsze testy SQL działają na Redis
# paczkowanie/transakcje
# wyniki w agregatach minutes??? ale to nie ma sensu, więc może posprzątać SQL
# poprawność cudzysłowów we wszystkich fazach zapisu i odczytu

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
# może trzeba pousuwać minutes, bo to nie ma sensu
