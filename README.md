## TODO wdrażanie REDIS
# zadziałanie sample_results
# przetestowanie ręczne z ping-show w pełnym zakresie
# pełny przegląd co zrobić z parametrami zapytań SQL
# testy dla rozbudowanego get_pings_redis
# sprawdzenie ping-proble
# deployment na heroku
# deployment na AWS
# test długotrwały probe-chmura
# parametry ze środowiska
# zachowania przy braku parametrów obowiązkowych
# zautomatyzowana budowa środowiska
# wszystkie wcześniejsze testy SQL działają na Redis
# implementacja metod delete

## TODO merge REDIS + SQL
# porządkowanie zdublowanych metod SQL na styku z Flask (pseudo, ...)
# struktury danych PingResult i sensowne+jednolite przekazywanie parametrów/wyników
# SQL przechodzi wszystkie testy Redis
# łączenie lub porządkowanie testów
# uniezależnianie testów od magazynu
# parametry do testowania ze środowiska
# jeden skrypt testowy na cały SQL+Redis
# przegląd i ocena pokrycia testami
# łączenie index
# index/makedb tylko dla SQL? automatyczne rozpoznanie?
# testowanie naprzemienne ping-show, może coś zautomatyzować?