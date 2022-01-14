### Tezos DeFi Hackathon 2022: Juster Challenge Starter Kit

В данном репозитории находятся материалы которые должны упростить процесс знакомства с Juster и предложить участникам хакатона возможные пути решения представленного челленжа.

### Challenge: Интеграция с протоколом Juster
Сервис позволяющий взаимодействовать с Juster используя информацию о событиях и ставках пользователей

### Juster
[Juster](https://juster.fi/) это платформа позволяющая пользователям взаимодействовать на рынке рисков и ставок в различных ролях: создавая события, предоставляя ликвидность и делая ставки в отношении исходов этих событий. Принципы работы протокола описаны в [документации](https://app.juster.fi/docs/introduction)

На момент старта хакатона Juster состоит из одного смарт-контракта развернутого в тестовой сети Tezos hangzhou2net по адресу: [KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn](https://hangzhou2net.tzkt.io/KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn/operations/)

#### Используемая терминология:
- Event (ивент, событие) - структура данных в Juster, описывающая событие (динамика изменения курса валютной пары за определённый период), которое может иметь два результата: событие реализовано в соответствии с заданными характеристиками или нет
- Views - механизм взаимодействия между смарт-контрактами, позволяющий сторонним контрактам считывать информацию о состоянии контракта реализовавшего onchain views

Предложенная на хакатоне задача предлагает участникам сделать свой сервис который будет интегрироваться с Juster-ом используя его [contract views](https://hangzhou2net.tzkt.io/KT197iHRJaAGw3oGpQj21YYV1vK9Fa5ShoMn/views):
* `getNextEventId` - позволяет получить id по которому будет доступен следующий ивент, который будет создан Juster-ом. Эта информация может использоваться для создания новых ивентов используя сторонний смарт-контракт с сохранением в нём id вновь созданных ивентов
* `getPosition` - позволяет получить информацию о предоставленной ликвидности и сделанных ставках по адресу пользователя и id события
* `getEvent` - позволяет получить информацию о текущем статусе и характеристиках события по его id
* `isParticipatedInEvent` - позволяет узнать участвовал ли пользователь в ивенте по его адресу и id события

### Возможные примеры реализации задачи в рамках хакатона:
1. Ревард-программа вознаграждающая участников протокола за ставки и предоставление ликвидности. Награды могут быть в виде xtz, NFT или FT токенов, условия выдачи награды могут быть любыми.
2. DeFi инструмент который делает ставки / предоставляет ликвидость или делает комбинированные операции при наступлении определённых условий.
3. Агрегатор ликвидности пользователей.
4. Арбитраж ставок с помощью смарт-контракта.

[Пример reward-программы](reward.ligo) использующей Juster onchain views (можно использовать в качестве baseline для решения в хакатоне).

### Что ожидается в результате челленджа:
1. Опубликованный репозиторий с кодом решения, включющий в себя:
    - смарт-контракт интегрированный с onchain views Juster. Данный контракт должен реализовать интересную и/или полезную логику, расширяющую возможности протокола. Для написания контракта желательно использовать язык [LIGO](https://ligolang.org/).
    - приложение UI позволяющее взаимодействовать с этим контрактом
2. Смарт контракт должен быть задеплоен в сети hangzhou2net
3. Ссылка на работающее веб приложение позволяющее пользователям взаимодействовать с этим смарт контрактом будет преимуществом
4. Наличие тестов на смарт конракт будет преимуществом

