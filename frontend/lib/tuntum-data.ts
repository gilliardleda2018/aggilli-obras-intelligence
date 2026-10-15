export type WeeklyItem={name:string;work:string;project:string;amount:number;category:"Mão de obra"|"Material"|"Serviço"|"Combustível"|"Equipamento"|"Outros";notes?:string};
export const locations=["Casa BDC / Casa Barra","Casa da Érica","MG Coco — Confinamento","MG Coco — Garagem","MG Tabocal","MG Cipó","MG Olho d'Água","Procuradoria","Escritório da Bruna","Casa da Aider","Casa do Nelson","Rua 12","MG Garagem","Santa Filomena"];
export const payroll:WeeklyItem[]=[
{name:"Ribamar (Riba)",work:"Assentamento de cerâmica",project:"Casa BDC / Casa Barra",amount:800,category:"Mão de obra"},
{name:"Antonio José",work:"Reforma e substituição de telhas; 1 pedreiro e 1 servente",project:"Casa BDC / Casa Barra",amount:1150,category:"Mão de obra",notes:"Relato também menciona reforma da casa da Érica; conferir alocação"},
{name:"Cabiludo",work:"Estrutura e ampliação do galpão do confinamento",project:"MG Coco — Confinamento",amount:1500,category:"Mão de obra",notes:"Relato inclui reparos na Rua 12"},
{name:"José das Cruz",work:"Móveis e marcenaria em diversos imóveis",project:"Procuradoria",amount:2000,category:"Mão de obra",notes:"Também Escritório da Bruna, Olho d'Água e Casa da Aider"},
{name:"Laércio",work:"Pintura e acabamento",project:"MG Tabocal",amount:2000,category:"Mão de obra",notes:"FOPAG 28/08 classifica como Tabocal; o relato de 14/10 aponta Casa BDC — conferir"},
{name:"Juarez",work:"Estrutura do galpão de garagem",project:"MG Coco — Garagem",amount:1500,category:"Mão de obra",notes:"Relato indica R$ 2.000,00; folha registra R$ 1.500,00"},
{name:"JK Metalúrgica / Kleyton",work:"Estrutura do galpão de garagem",project:"MG Tabocal",amount:3000,category:"Mão de obra",notes:"Fornecedor nomeado como Kleyton na FOPAG"},
{name:"Marcelo Construções",work:"Argamassa, cimento e materiais gerais",project:"Diversas obras",amount:5000,category:"Material",notes:"Dívida relatada: R$ 24.670,00; lançamento descrito como 'de haver'"},
{name:"Gardel",work:"Colunas e vergalhões para dique, galpão, chiqueiro e cochos",project:"MG Coco — Confinamento",amount:2000,category:"Material",notes:"Dívida relatada: R$ 4.009,50; múltiplas obras"},
{name:"Aluvidros",work:"Pias, portas, box e materiais de acabamento",project:"MG Tabocal",amount:2000,category:"Material",notes:"Dívida relatada: R$ 5.715,00; múltiplas obras"},
{name:"Darlan",work:"Cimento, rejunte, conexões e espaçadores",project:"Casa BDC / Casa Barra",amount:935,category:"Material",notes:"Comprovantes mencionados no relato"},
{name:"Posto Ana Luiza",work:"Abastecimentos de veículos e apoio à pintura",project:"Diversas obras",amount:985.87,category:"Combustível",notes:"Quatro itens somam R$ 985,87; texto também indica R$ 935,00"},
{name:"Bruno Muck",work:"6 horas de munck e deslocamento para soldagem",project:"MG Coco — Confinamento",amount:3480,category:"Equipamento"},
{name:"Renata",work:"Sondagem do solo",project:"MG Garagem",amount:1600,category:"Serviço",notes:"Contrato relatado R$ 3.200,00 em duas parcelas; texto também indica R$ 1.800,00"},
{name:"Erika",work:"Complemento de móveis do quarto dos gêmeos",project:"Casa BDC / Casa Barra",amount:3500,category:"Serviço"},
{name:"Rodrigo",work:"Serviços no Cipó",project:"MG Cipó",amount:120,category:"Serviço"}
];
export const contracts=[
{project:"Casa BDC / Casa Barra",name:"Edilton",total:8000,advance:7500,balance:500},
{project:"MG Tabocal",name:"Raimundo BR",total:38000,advance:27500,balance:5000},
{project:"MG Coco — Garagem",name:"Cabiludo",total:72000,advance:21300,balance:4500},
{project:"Procuradoria",name:"José das Cruz",total:64800,advance:56000,balance:8800},
{project:"Casa BDC / Casa Barra",name:"Ipapel Teresina (plotagem)",total:0,advance:9000,balance:9000},
{project:"Casa BDC / Casa Barra",name:"Master Vidros",total:15869.72,advance:14490,balance:1379.72},
{project:"Casa BDC / Casa Barra",name:"Thiago PK",total:3500,advance:2500,balance:1000},
{project:"MG Tabocal",name:"Laércio",total:41500,advance:32500,balance:9000},
{project:"Santa Filomena",name:"Vando",total:450000,advance:25000,balance:425000},
{project:"MG Coco — Garagem",name:"Juarez",total:13000,advance:10493,balance:2507},
{project:"MG Tabocal",name:"Kleyton",total:23500,advance:6000,balance:17500},
{project:"MG Olho d'Água",name:"Francisco",total:6000,advance:2100,balance:3900}
];
export const suppliers=[{name:"Marcelo Construções",debt:24670,planned:5000},{name:"Gardel",debt:4009.50,planned:2000},{name:"Aluvidros",debt:5715,planned:2000}];
export const activities=[
{project:"Casa BDC / Casa Barra",description:"Instalação de cerâmica, substituição de telhas e retoques de pintura"},
{project:"MG Coco — Confinamento",description:"Estrutura do galpão, ampliação de compartimento e soldagem das tesouras"},
{project:"MG Coco — Garagem",description:"Início da estrutura do galpão"},
{project:"MG Tabocal",description:"Estrutura do galpão de garagem"},
{project:"MG Cipó",description:"Serviços diversos e materiais para o chiqueiro"},
{project:"Procuradoria",description:"Móveis finalizados"},
{project:"MG Olho d'Água",description:"Móveis do escritório finalizados"}
];
export const money=(n:number)=>n.toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
