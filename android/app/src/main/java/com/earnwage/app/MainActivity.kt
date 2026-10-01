package com.earnwage.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.CancellationException
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

private val navy = Color(0xFF092733)
private val teal = Color(0xFF087F73)
private val cream = Color(0xFFF6F7F4)
private val gold = Color(0xFFF1D28C)
private val fallbackCountries = listOf(
    Place("PT","Portugal","EUR"),Place("ES","Spain","EUR"),Place("DE","Germany","EUR"),
    Place("FR","France","EUR"),Place("GB","United Kingdom","GBP"),Place("IN","India","INR"),
    Place("BR","Brazil","BRL"),Place("PK","Pakistan","PKR"),Place("NL","Netherlands","EUR"),
    Place("CH","Switzerland","CHF"),Place("IT","Italy","EUR"),Place("IE","Ireland","EUR"),
    Place("US","United States","USD"),Place("CA","Canada","CAD")
)
private val currencies = listOf("EUR","USD","GBP","CAD","CHF","BRL","INR","PKR")
private val feeds = listOf("all","remotive","arbeitnow","himalayas","jobicy","remoteok","greenhouse","lever","ashby")
private data class Place(val code:String,val name:String,val currency:String)
private data class Profession(val id:String,val name:String)
private data class Region(val code:String,val name:String)

private fun enc(s:String) = URLEncoder.encode(s,"UTF-8")
private fun number(n:Double):String = String.format(Locale.getDefault(),"%,.2f",n)
private fun money(n:Double,c:String):String = number(n)+" "+c
private fun numeric(raw:String):Double? = raw.trim().replace(" ","").replace(",",".").toDoubleOrNull()
private val insightsIndicators = listOf("inflation_annual","unemployment","gdp_per_capita","ppp_private_consumption","life_expectancy","gini","internet_use")
private fun indicatorTitle(code:String,lang:String):String {
    val pt=mapOf("inflation_annual" to "Inflação","unemployment" to "Desemprego",
        "gdp_per_capita" to "PIB per capita","ppp_private_consumption" to "PPP — consumo privado",
        "life_expectancy" to "Esperança de vida","gini" to "Desigualdade (Gini)",
        "internet_use" to "Utilização da Internet")
    val en=mapOf("inflation_annual" to "Inflation","unemployment" to "Unemployment",
        "gdp_per_capita" to "GDP per capita","ppp_private_consumption" to "PPP — private consumption",
        "life_expectancy" to "Life expectancy","gini" to "Inequality (Gini)",
        "internet_use" to "Internet usage")
    return (if(lang=="pt") pt else en)[code] ?: code
}
private fun salaryLabel(job:JSONObject,lang:String):String {
    val explicit = job.optString("salary_text","").trim()
    if (explicit.isNotEmpty() && explicit != "null") return explicit
    val unreported = mapOf("pt" to "Não divulgado","en" to "Not disclosed","es" to "No publicado",
        "fr" to "Non communiqué","de" to "Nicht angegeben","it" to "Non divulgato",
        "nl" to "Niet vermeld")
    return unreported[lang] ?: "Not disclosed"
}
private suspend fun api(path:String):JSONObject = withContext(Dispatchers.IO) {
    val connection = URL(BuildConfig.API_BASE_URL + path).openConnection() as HttpURLConnection
    try {
        connection.connectTimeout=12000
        connection.readTimeout=30000
        connection.setRequestProperty("Accept","application/json")
        val code=connection.responseCode
        val raw=(if(code in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() } ?: ""
        if(code !in 200..299) throw IllegalStateException("HTTP " + code + ": " + raw.take(120))
        JSONObject(raw)
    } finally { connection.disconnect() }
}
class MainActivity:ComponentActivity() {
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { EarnWage() }
    }
}

@Composable private fun EarnWage() {
    val context=LocalContext.current
    val prefs=remember { context.getSharedPreferences("earnwage_settings",Context.MODE_PRIVATE) }
    var lang by remember { mutableStateOf(prefs.getString("language",Locale.getDefault().language.takeIf { it in languageNames } ?: "en") ?: "en") }
    var country by remember { mutableStateOf(prefs.getString("country","PT") ?: "PT") }
    var dest by remember { mutableStateOf(prefs.getString("destination","US") ?: "US") }
    var currency by remember { mutableStateOf(prefs.getString("currency","EUR") ?: "EUR") }
    var appearance by remember { mutableStateOf(prefs.getString("theme","system") ?: "system") }
    var onboarded by remember { mutableStateOf(prefs.getBoolean("onboarded",false)) }
    var page by remember { mutableStateOf("home") }
    var occupation by remember { mutableStateOf("software_developer") }
    var countries by remember { mutableStateOf(fallbackCountries) }
    var professions by remember { mutableStateOf(emptyList<Profession>()) }
    var region by remember { mutableStateOf("") }
    var regionB by remember { mutableStateOf("") }
    var regions by remember { mutableStateOf(emptyList<Region>()) }
    var regionsB by remember { mutableStateOf(emptyList<Region>()) }
    var apiVersion by remember { mutableStateOf("?") }
    var connectivity by remember { mutableStateOf("") }
    var remoteOnly by remember { mutableStateOf(false) }
    var salaryOnly by remember { mutableStateOf(false) }
    var age by remember { mutableIntStateOf(90) }
    var feed by remember { mutableStateOf("all") }
    var annual by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("1000") }
    var previous by remember { mutableStateOf("") }
    var current by remember { mutableStateOf("") }
    var enteredInflation by remember { mutableStateOf("") }
    var fromYear by remember { mutableStateOf("2020") }
    var toYear by remember { mutableStateOf("2026") }
    var request by remember { mutableStateOf("") }
    var requestId by remember { mutableIntStateOf(0) }
    var fxFrom by remember { mutableStateOf("EUR") }
    var fxTo by remember { mutableStateOf("USD") }
    var fxId by remember { mutableIntStateOf(0) }
    var fxResult by remember { mutableStateOf<JSONObject?>(null) }
    var fxError by remember { mutableStateOf("") }
    var fxLoading by remember { mutableStateOf(false) }
    var wageFx by remember { mutableStateOf<Map<String,JSONObject>>(emptyMap()) }
    var globalId by remember { mutableIntStateOf(0) }
    var globalResults by remember { mutableStateOf<List<Pair<Place,JSONObject>>>(emptyList()) }
    var globalFx by remember { mutableStateOf<Map<String,JSONObject>>(emptyMap()) }
    var globalLoading by remember { mutableStateOf(false) }
    var globalError by remember { mutableStateOf("") }
    var insightCountries by remember { mutableStateOf(listOf("PT","ES")) }
    var insightIndicator by remember { mutableStateOf("inflation_annual") }
    var insightId by remember { mutableIntStateOf(0) }
    var insightData by remember { mutableStateOf<JSONObject?>(null) }
    var insightError by remember { mutableStateOf("") }
    var insightLoading by remember { mutableStateOf(false) }
    var requestPage by remember { mutableStateOf("") }
    var response by remember { mutableStateOf<JSONObject?>(null) }
    var error by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    fun navigate(next:String) { page=next; request=""; requestId++; response=null; error=""; loading=false }
    fun search(path:String) { response=null; error=""; requestPage=page; request=path; requestId++ }
    val dark=when(appearance) {
        "dark" -> true
        "light" -> false
        else -> androidx.compose.foundation.isSystemInDarkTheme()
    }
    val palette=if(dark) darkColorScheme(primary=gold,secondary=Color(0xFF60CCB2),
        background=Color(0xFF071B23),surface=Color(0xFF102F3B),onSurface=Color.White)
    else lightColorScheme(primary=teal,secondary=navy,background=cream,
        surface=Color.White,onSurface=navy)
    LaunchedEffect(Unit) {
        try {
            val h=api("/v1/health")
            apiVersion=h.optString("version","?")
            val arr=api("/v1/countries").optJSONArray("countries") ?: JSONArray()
            if(arr.length()>0) countries=(0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
                .map { Place(it.optString("code"),it.optString("name"),it.optString("currency")) }
            connectivity="OK"
        } catch(e:Exception) { connectivity=e.message ?: "Network error" }
    }
    LaunchedEffect(lang) {
        prefs.edit().putString("language",lang).apply()
        try {
            val arr=api("/v1/occupations?lang=" + enc(lang)).optJSONArray("occupations") ?: JSONArray()
            professions=(0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
                .map { Profession(it.optString("id"),it.optString("label")) }
        } catch(e:Exception) { if(professions.isEmpty()) connectivity=e.message ?: "Network error" }
    }
    LaunchedEffect(country) {
        prefs.edit().putString("country",country).apply()
        region=""
        regions=if(country in listOf("US","CA")) try {
            parseRegions(api("/v1/regions/"+country))
        } catch (_:Exception) { emptyList() } else emptyList()
    }
    LaunchedEffect(dest) {
        prefs.edit().putString("destination",dest).apply()
        regionB=""
        regionsB=if(dest in listOf("US","CA")) try {
            parseRegions(api("/v1/regions/"+dest))
        } catch (_:Exception) { emptyList() } else emptyList()
    }
    LaunchedEffect(currency) { prefs.edit().putString("currency",currency).apply() }
    LaunchedEffect(appearance) { prefs.edit().putString("theme",appearance).apply() }
    LaunchedEffect(requestId) {
        if(request.isNotBlank()) {
            val target=requestPage
            val requestPath=request
            loading=true
            try {
                val data=api(requestPath)
                if(page==target && request==requestPath) response=data
            } catch(e:Exception) {
                if(e is CancellationException) throw e
                if(page==target && request==requestPath) error=if(page=="inflation" || page=="power") "Dados de inflação indisponíveis para este período." else "Não foi possível atualizar. Tenta novamente."
            } finally { if(page==target && request==requestPath) loading=false }
        }
    }
    LaunchedEffect(fxId) {
        if(fxId==0) return@LaunchedEffect
        val from=fxFrom; val to=fxTo; val initial=numeric(amount)
        fxResult=null; fxError=""; fxLoading=true
        try {
            require(initial!=null && initial>=0) { "Introduz um montante válido." }
            val first=if(from=="EUR") JSONObject().put("units_per_eur",1.0).put("period","") else api("/v1/exchange-rates/"+from)
            val second=if(to=="EUR") JSONObject().put("units_per_eur",1.0).put("period","") else api("/v1/exchange-rates/"+to)
            val a=first.optDouble("units_per_eur",Double.NaN); val b=second.optDouble("units_per_eur",Double.NaN)
            require(a.isFinite() && b.isFinite() && a>0 && b>0) { "Taxa de câmbio indisponível." }
            val dateA=first.optString("period"); val dateB=second.optString("period")
            require(dateA.isBlank() || dateB.isBlank() || dateA==dateB) { "As taxas têm datas diferentes. Tenta novamente." }
            fxResult=JSONObject().put("from",from).put("to",to).put("value",initial*b/a)
                .put("rate",b/a).put("period",if(dateB.isNotBlank()) dateB else dateA)
        } catch(e:Exception) {
            if(e is CancellationException) throw e
            fxError=e.message?.takeIf { !it.startsWith("HTTP ") } ?: "Não foi possível obter as taxas. Tenta novamente."
        } finally { fxLoading=false }
    }
    LaunchedEffect(currency,response,page) {
        wageFx=emptyMap()
        if(page !in listOf("salary","compare") || response==null) return@LaunchedEffect
        val sides=if(page=="salary") listOfNotNull(response) else
            listOfNotNull(response?.optJSONObject("country_a"),response?.optJSONObject("country_b"))
        val sourceCurrencies=sides.mapNotNull { it.optJSONObject("annual_presentation")
            ?.takeIf { row -> row.optString("status")=="available" }?.optString("currency") }
            .filter { it.isNotBlank() && it!=currency }.toSet()
        if(sourceCurrencies.isEmpty()) return@LaunchedEffect
        try {
            val codes=sourceCurrencies+currency
            val collected=mutableMapOf<String,JSONObject>()
            for(code in codes) {
                collected[code]=if(code=="EUR") JSONObject().put("units_per_eur",1.0).put("period","")
                    else api("/v1/exchange-rates/"+code)
            }
            wageFx=collected
        } catch(e:Exception) { if(e is CancellationException) throw e }
    }
    LaunchedEffect(globalId) {
        if(globalId==0) return@LaunchedEffect
        globalLoading=true; globalError=""; globalResults=emptyList(); globalFx=emptyMap()
        try {
            val rows=mutableListOf<Pair<Place,JSONObject>>()
            for(place in countries) {
                try { rows += place to api("/v1/earnwage/overview?country="+place.code+"&occupation="+enc(occupation)) }
                catch (_:Exception) { }
            }
            globalResults=rows
            val needed=(rows.flatMap { (_,d) -> salaryCurrencies(d) } + currency).filter { it.isNotBlank() }.toSet()
            val rates=mutableMapOf<String,JSONObject>()
            for(code in needed) rates[code]=if(code=="EUR") JSONObject().put("units_per_eur",1.0).put("period","")
                else api("/v1/exchange-rates/"+code)
            globalFx=rates
        } catch(e:Exception) {
            if(e is CancellationException) throw e
            globalError=if(lang=="pt") "Não foi possível concluir a pesquisa global." else "Could not complete global search."
        } finally { globalLoading=false }
    }
    LaunchedEffect(insightId) {
        if(insightId==0) return@LaunchedEffect
        val codes=insightCountries.toList(); val indicator=insightIndicator
        insightData=null; insightError=""; insightLoading=true
        try {
            val results=JSONObject()
            for(code in codes) {
                results.put(code,api("/v1/countries/"+code+"/indicators/"+indicator+"?history=true"))
            }
            insightData=results
        } catch(e:Exception) {
            if(e is CancellationException) throw e
            insightError="Não foi possível consultar os indicadores. Tenta novamente."
        } finally { insightLoading=false }
    }
    BackHandler(enabled=onboarded && page!="home") { navigate("home") }
    MaterialTheme(colorScheme=palette) {
        Scaffold(containerColor=MaterialTheme.colorScheme.background,
            bottomBar={
                if(onboarded) NavigationBar(containerColor=MaterialTheme.colorScheme.surface) {
                    listOf("home","compare","jobs","settings").forEach { destination ->
                        val symbol=when(destination) {"home"->"⌂";"compare"->"⇄";"jobs"->"▣";else->"⚙"}
                        NavigationBarItem(selected=page==destination, onClick={navigate(destination)},
                            icon={Text(symbol,fontSize=21.sp)},
                            label={Text(tr(lang,destination),maxLines=1,fontSize=10.sp)})
                    }
                }
            }
        ) { inset ->
            LazyColumn(modifier=Modifier.fillMaxSize().padding(inset),
                contentPadding=PaddingValues(horizontal=18.dp,vertical=16.dp),
                verticalArrangement=Arrangement.spacedBy(14.dp)) {
                item {
                    Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(11.dp)) {
                        Image(painterResource(R.drawable.earnwage_logo),contentDescription="EarnWage",
                            modifier=Modifier.size(49.dp),contentScale=ContentScale.Fit)
                        Column(Modifier.weight(1f)) {
                            Text("EarnWage",fontWeight=FontWeight.Bold,fontSize=27.sp)
                            Text(tr(lang,"welcome"),color=MaterialTheme.colorScheme.secondary,fontSize=12.sp)
                        }
                        if(onboarded) TextButton(onClick={navigate("settings")}) { Text("⚙",fontSize=22.sp) }
                    }
                }
                if(!onboarded) {
                    item {
                        Image(painterResource(R.drawable.earnwage_hero),contentDescription="EarnWage",
                            modifier=Modifier.fillMaxWidth().height(170.dp),contentScale=ContentScale.Fit)
                        Heading(tr(lang,"choose"))
                    }
                    item { LanguageMenu(lang) { lang=it } }
                    item { PlaceMenu(tr(lang,"country"),countries,country) { country=it } }
                    item { CurrencyMenu(lang,currency) { currency=it } }
                    item { ThemeMenu(lang,appearance) { appearance=it } }
                    item {
                        Button(onClick={
                            onboarded=true
                            prefs.edit().putBoolean("onboarded",true).apply()
                            navigate("home")
                        },modifier=Modifier.fillMaxWidth().height(52.dp)) { Text(tr(lang,"start")) }
                    }
                } else {
                    when(page) {
                        "home" -> {
                            item {
                                Image(painterResource(R.drawable.earnwage_hero),contentDescription="EarnWage",
                                    modifier=Modifier.fillMaxWidth().height(164.dp),contentScale=ContentScale.Fit)
                            }
                            item { Heading(tr(lang,"welcome")) }
                            item { Feature("⇄",tr(lang,"compare"),tr(lang,"salary")) {navigate("compare")} }
                            item { Feature("▥",if(lang=="pt") "Comparar países" else "Country insights",if(lang=="pt") "Gráficos e indicadores económicos" else "Economic charts and indicators") {navigate("insights")} }
                            item { Feature("▣",tr(lang,"jobs"),tr(lang,"jobnote")) {navigate("jobs")} }
                            item { Feature("◎",if(lang=="pt") "Salários pelo mundo" else "Global salaries",if(lang=="pt") "Pesquisa uma profissão nos 14 países" else "Search one occupation across 14 countries") {navigate("global")} }
                            item { Feature("◈",tr(lang,"salary"),tr(lang,"official")) {navigate("salary")} }
                            item { Feature("⊕",tr(lang,"tools"),tr(lang,"more")) {navigate("tools")} }
                            item { Caption(countryFlag(country)+" "+(countries.find { it.code==country }?.name ?: country)+
                                " · "+tr(lang,"currency")+": "+currency+" · API "+apiVersion) }
                        }
                        "global" -> {
                            item { Heading(if(lang=="pt") "Salários pelo mundo" else "Global salaries") }
                            item { Caption(if(lang=="pt") "Pesquisa uma profissão e compara as três camadas oficiais disponíveis em cada país." else "Search an occupation and compare the three official salary layers available in each country.") }
                            item { ProfessionMenu(tr(lang,"profession"),professions,occupation,lang) {occupation=it} }
                            item { CurrencyMenu(lang,currency) {currency=it} }
                            item {
                                Button(onClick={globalId++},enabled=professions.isNotEmpty()&&!globalLoading,
                                    modifier=Modifier.fillMaxWidth()) {
                                    Text(if(lang=="pt") "Pesquisar nos 14 países" else "Search 14 countries")
                                }
                            }
                            item { SalaryLegend(lang) }
                            if(globalLoading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                            if(globalError.isNotBlank()) item { Metric(tr(lang,"unavailable"),globalError) }
                            if(globalResults.isNotEmpty()) {
                                item { Caption((if(lang=="pt") "Resultados: " else "Results: ")+globalResults.size+" · "+currency) }
                                items(globalResults,key={it.first.code}) { (place,data) ->
                                    GlobalSalaryCard(place,data,lang,currency,globalFx)
                                }
                            }
                        }
                        "compare","salary" -> {
                            item { Heading(tr(lang,if(page=="compare") "compare" else "salary")) }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it} }
                            if(regions.isNotEmpty()) item { RegionMenu(tr(lang,"region"),regions,region) { region=it } }
                            if(page=="compare") {
                                item { PlaceMenu(tr(lang,"destination"),countries,dest) {dest=it} }
                                if(regionsB.isNotEmpty()) item {RegionMenu(tr(lang,"region"),regionsB,regionB) {regionB=it} }
                            }
                            item { ProfessionMenu(tr(lang,"profession"),professions,occupation,lang) {occupation=it} }
                            if(page=="salary") item { NumberBox(tr(lang,"annual"),annual) {annual=it} }
                            item {
                                Button(onClick={
                                    val selected=enc(occupation)
                                    val path=if(page=="salary") "/v1/earnwage/overview?country="+country+
                                        "&occupation="+selected+
                                        (if(region.isNotBlank()) "&region="+region else "")+
                                        (annual.toDoubleOrNull()?.takeIf {it>0}?.let {"&annual_gross="+it} ?: "")
                                    else "/v1/earnwage/compare?country_a="+country+"&country_b="+dest+
                                        "&occupation="+selected+
                                        (if(region.isNotBlank()) "&region_a="+region else "")+
                                        (if(regionB.isNotBlank()) "&region_b="+regionB else "")
                                    search(path)
                                },enabled=professions.isNotEmpty(),modifier=Modifier.fillMaxWidth()) {
                                    Text(tr(lang,"search"))
                                }
                            }
                            
                        }
                        "jobs" -> {
                            item { Heading(tr(lang,"jobs")) }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it} }
                            item { ProfessionMenu(tr(lang,"profession"),professions,occupation,lang) {occupation=it} }
                            item { Heading(tr(lang,"filters"),20) }
                            item { CheckRow(tr(lang,"remote"),remoteOnly) {remoteOnly=it} }
                            item { CheckRow(tr(lang,"disclosed"),salaryOnly) {salaryOnly=it} }
                            item { SelectMenu(tr(lang,"source"),feeds,feed) {feed=it} }
                            item { SelectMenu(tr(lang,"age"),listOf("30","90","180"),age.toString()) {age=it.toInt()} }
                            item {
                                Button(onClick={
                                    search("/v1/jobs?country="+country+"&occupation="+enc(occupation)+
                                        "&provider="+feed+"&salary_published="+salaryOnly+
                                        "&max_age_days="+age+"&limit=100")
                                },enabled=professions.isNotEmpty(),modifier=Modifier.fillMaxWidth()) {
                                    Text(tr(lang,"search"))
                                }
                            }
                            
                        }
                        "tools" -> {
                            item { Heading(tr(lang,"tools")) }
                            item { Feature("↗",tr(lang,"inflation"),tr(lang,"official")) {navigate("inflation")} }
                            item { Feature("◈",tr(lang,"power"),tr(lang,"powernote")) {navigate("power")} }
                            item { Feature("⇆",tr(lang,"exchange"),tr(lang,"fxnote")) {navigate("exchange")} }
                            item { Feature("▥",if(lang=="pt") "Comparar países" else "Country insights",if(lang=="pt") "Inflação e desemprego com gráficos" else "Economic charts") {navigate("insights")} }
                        }
                        "inflation","power" -> {
                            item { Heading(tr(lang,if(page=="inflation") "inflation" else "power")) }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it;response=null} }
                            item { NumberBox(tr(lang,"yearfrom"),fromYear) {fromYear=it} }
                            item { NumberBox(tr(lang,"yearto"),toYear) {toYear=it} }
                            if(page=="power") {
                                item { NumberBox(if(lang=="pt") "Salário inicial ("+currency+")" else "Initial salary ("+currency+")",previous) {previous=it} }
                                item { NumberBox(if(lang=="pt") "Salário atual ("+currency+", opcional)" else "Current salary ("+currency+", optional)",current) {current=it} }
                            }
                            item {
                                Button(onClick={search("/v1/countries/"+country+"/indicators/inflation_annual?history=true")},
                                    enabled=(fromYear.toIntOrNull() ?: 0)<(toYear.toIntOrNull() ?: 0) &&
                                    (page!="power" || (numeric(previous) ?: 0.0)>0),
                                    modifier=Modifier.fillMaxWidth()) {Text(tr(lang,"calculate"))}
                            }
                        }
                        "exchange" -> {
                            item { Heading(tr(lang,"exchange")) }
                            item { SelectMenu(if(lang=="pt") "Moeda de origem" else "From currency",currencies,fxFrom) {fxFrom=it;fxResult=null} }
                            item { SelectMenu(if(lang=="pt") "Moeda de destino" else "To currency",currencies,fxTo) {fxTo=it;fxResult=null} }
                            item { OutlinedButton(onClick={
                                val old=fxFrom; fxFrom=fxTo; fxTo=old; fxResult=null
                            },modifier=Modifier.fillMaxWidth()) {Text(if(lang=="pt") "⇄ Inverter moedas" else "⇄ Swap currencies")} }
                            item { NumberBox(if(lang=="pt") "Montante em "+fxFrom else "Amount in "+fxFrom,amount) {amount=it;fxResult=null} }
                            item { Button(onClick={fxId++},modifier=Modifier.fillMaxWidth()) {Text(tr(lang,"calculate"))} }
                            if(fxLoading) item {CircularProgressIndicator()}
                            if(fxError.isNotBlank()) item {Metric(tr(lang,"unavailable"),fxError)}
                            fxResult?.let { result ->
                                item {Metric(if(lang=="pt") "Valor convertido" else "Converted amount",
                                    money(result.optDouble("value"),result.optString("to")),
                                    "1 "+result.optString("from")+" = "+number(result.optDouble("rate"))+
                                    " "+result.optString("to")+" · "+result.optString("period")+" · ECB")}
                            }
                        }
                        "insights" -> {
                            item {
                                CountryInsightsDashboard(countries.map { it.code to it.name },
                                    currency, lang)
                            }
                        }
                        "settings" -> {
                            item { Heading(tr(lang,"settings")) }
                            item { LanguageMenu(lang) {lang=it} }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it} }
                            item { CurrencyMenu(lang,currency) {currency=it} }
                            item { ThemeMenu(lang,appearance) {appearance=it} }
                            item { Caption(tr(lang,"settingsnote")+"\n"+tr(lang,"countryhint")) }
                            item { Feature("ⓘ",tr(lang,"about"),tr(lang,"data")) {navigate("about")} }
                        }
                        "about" -> {
                            item { Heading(tr(lang,"about")) }
                            item { Metric("EarnWage","v"+BuildConfig.VERSION_NAME,
                                "com.earnwage.app · Gil Pereira") }
                            item { Metric(tr(lang,"apiversion"),apiVersion,BuildConfig.API_BASE_URL) }
                            item { Caption("Your salary. Your world.\n14 countries · 40 occupations · 7 interface languages") }
                            item { Caption("Eurostat · ECB · ILOSTAT · BLS · Canada Job Bank · Remotive · Arbeitnow · Himalayas · Jobicy · Remote OK · Greenhouse · Lever · Ashby") }
                            item { Caption(tr(lang,"wagesnote")+"\n"+tr(lang,"nethint")+"\n"+tr(lang,"jobnote")) }
                        }
                    }
                    if(loading) item { CircularProgressIndicator() }
                    if(error.isNotBlank()) item {
                        Metric(tr(lang,"unavailable"),error)
                        TextButton(onClick={requestId++}) {Text(if(lang=="pt") "Tentar novamente" else "Retry")}
                    }
                    response?.let { data ->
                        if(page=="jobs") {
                            val arr=data.optJSONArray("jobs") ?: JSONArray()
                            val listings=(0 until arr.length()).mapNotNull {arr.optJSONObject(it)}
                                .filter { !remoteOnly || it.optBoolean("remote",false) }
                            item { Metric(tr(lang,"results"),listings.size.toString(),
                                tr(lang,"source")+": "+feed+" · "+tr(lang,"age")+": "+age+" "+tr(lang,"days")) }
                            if(listings.isEmpty()) item { Caption(tr(lang,"noresults")) }
                            items(listings,key={it.optString("id")}) { JobCard(it,lang) }
                            if(data.optInt("count")>arr.length()) item {
                                Caption("Showing first "+arr.length()+" results; refine filters to narrow the search.")
                            }
                        } else if(page in listOf("salary","compare","inflation","power","exchange")) {
                            item { ApiResult(page,data,lang,country,fromYear,toYear,numeric(previous),numeric(current),numeric(amount),currency,wageFx) }
                        }
                    }
                }
            }
        }
    }
}
private fun parseRegions(data:JSONObject):List<Region> {
    val arr=data.optJSONArray("options") ?: JSONArray()
    return (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
        .map {Region(it.optString("code"),it.optString("name"))}
}

@Composable private fun Heading(label:String,size:Int=25) {
    Text(label,fontSize=size.sp,fontWeight=FontWeight.Bold,color=MaterialTheme.colorScheme.onSurface)
}
@Composable private fun Caption(text:String) {
    Text(text,fontSize=12.sp,color=MaterialTheme.colorScheme.onSurface.copy(alpha=.72f))
}
@Composable private fun Metric(title:String,value:String,detail:String="") {
    Card(shape=RoundedCornerShape(18.dp),modifier=Modifier.fillMaxWidth(),
        colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
            Text(title,color=MaterialTheme.colorScheme.secondary,fontSize=13.sp,fontWeight=FontWeight.SemiBold)
            Text(value,color=MaterialTheme.colorScheme.onSurface,fontSize=19.sp,fontWeight=FontWeight.Bold)
            if(detail.isNotBlank()) Caption(detail)
        }
    }
}
@Composable private fun Feature(icon:String,title:String,subtitle:String,open:()->Unit) {
    Card(onClick=open,modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(18.dp),
        colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
        Row(Modifier.padding(17.dp),verticalAlignment=Alignment.CenterVertically,
            horizontalArrangement=Arrangement.spacedBy(14.dp)) {
            Text(icon,fontSize=29.sp,color=MaterialTheme.colorScheme.secondary)
            Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                Text(title,fontSize=18.sp,fontWeight=FontWeight.Bold)
                Caption(subtitle)
            }
            Text("›",fontSize=26.sp,color=MaterialTheme.colorScheme.secondary)
        }
    }
}
@Composable private fun NumberBox(label:String,value:String,change:(String)->Unit) {
    OutlinedTextField(value,change,modifier=Modifier.fillMaxWidth(),label={Text(label)},singleLine=true,
        keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Decimal))
}
@Composable private fun CheckRow(label:String,checked:Boolean,change:(Boolean)->Unit) {
    Row(Modifier.fillMaxWidth().clickable{change(!checked)}.padding(vertical=3.dp),
        verticalAlignment=Alignment.CenterVertically) {
        Text(label,Modifier.weight(1f))
        Switch(checked=checked,onCheckedChange=change)
    }
}
@Composable private fun SelectMenu(label:String,options:List<String>,value:String,change:(String)->Unit) {
    var expanded by remember {mutableStateOf(false)}
    Box {
        OutlinedButton(onClick={expanded=true},modifier=Modifier.fillMaxWidth()) {
            Text(label+": "+value,modifier=Modifier.weight(1f),maxLines=1,overflow=TextOverflow.Ellipsis)
            Text(" ▾")
        }
        DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}) {
            options.forEach {option->
                DropdownMenuItem(text={Text(option)},onClick={change(option);expanded=false})
            }
        }
    }
}
@Composable private fun LanguageMenu(lang:String,change:(String)->Unit) {
    var expanded by remember {mutableStateOf(false)}
    Box {
        OutlinedButton(onClick={expanded=true},modifier=Modifier.fillMaxWidth()) {
            Text(tr(lang,"language")+": "+(languageNames[lang] ?: lang),modifier=Modifier.weight(1f))
            Text(" ▾")
        }
        DropdownMenu(expanded=expanded,onDismissRequest={expanded=false}) {
            languageNames.forEach {(code,label)->
                DropdownMenuItem(text={Text(label)},onClick={change(code);expanded=false})
            }
        }
    }
}
@Composable private fun PlaceMenu(label:String,countries:List<Place>,value:String,change:(String)->Unit) {
    var opened by remember {mutableStateOf(false)}
    val selected=countries.firstOrNull {it.code==value}
    OutlinedButton(onClick={opened=true},modifier=Modifier.fillMaxWidth()) {
        Text(label+": "+countryFlag(value)+" "+(selected?.name ?: value),
            modifier=Modifier.weight(1f),maxLines=1,overflow=TextOverflow.Ellipsis)
        Text(" ▾")
    }
    if(opened) Dialog(onDismissRequest={opened=false}) {
        Surface(shape=RoundedCornerShape(20.dp),color=MaterialTheme.colorScheme.surface) {
            LazyColumn(Modifier.heightIn(max=510.dp),contentPadding=PaddingValues(12.dp)) {
                items(countries) {place->
                    Text(countryFlag(place.code)+"  "+place.name+" · "+place.currency,
                        modifier=Modifier.fillMaxWidth().clickable{
                            change(place.code);opened=false
                        }.padding(14.dp))
                    HorizontalDivider()
                }
            }
        }
    }
}
@Composable private fun ProfessionMenu(label:String,professions:List<Profession>,value:String,lang:String,change:(String)->Unit) {
    var opened by remember {mutableStateOf(false)}
    var filter by remember {mutableStateOf("")}
    val selected=professions.firstOrNull{it.id==value}
    OutlinedButton(onClick={opened=true},modifier=Modifier.fillMaxWidth()) {
        Text(label+": "+(selected?.name ?: value),modifier=Modifier.weight(1f),
            maxLines=1,overflow=TextOverflow.Ellipsis)
        Text(" ▾")
    }
    if(opened) Dialog(onDismissRequest={opened=false}) {
        Surface(shape=RoundedCornerShape(20.dp),color=MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(12.dp)) {
                OutlinedTextField(filter,{filter=it},modifier=Modifier.fillMaxWidth(),
                    label={Text(tr(lang,"search"))},singleLine=true)
                val matches=professions.filter {
                    it.name.contains(filter,ignoreCase=true) || it.id.contains(filter,ignoreCase=true)
                }
                LazyColumn(Modifier.heightIn(max=440.dp)) {
                    items(matches,key={it.id}) {profession->
                        Text(profession.name,modifier=Modifier.fillMaxWidth().clickable {
                            change(profession.id);opened=false;filter=""
                        }.padding(14.dp))
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}
@Composable private fun RegionMenu(label:String,regions:List<Region>,selected:String,change:(String)->Unit) {
    val choices=listOf(Region("","—"))+regions
    var opened by remember {mutableStateOf(false)}
    OutlinedButton(onClick={opened=true},modifier=Modifier.fillMaxWidth()) {
        Text(label+": "+(choices.firstOrNull{it.code==selected}?.name ?: selected),
            modifier=Modifier.weight(1f),maxLines=1)
        Text(" ▾")
    }
    if(opened) Dialog(onDismissRequest={opened=false}) {
        Surface(shape=RoundedCornerShape(20.dp),color=MaterialTheme.colorScheme.surface) {
            LazyColumn(Modifier.heightIn(max=510.dp),contentPadding=PaddingValues(12.dp)) {
                items(choices) {item->
                    Text(item.name,modifier=Modifier.fillMaxWidth().clickable {
                        change(item.code);opened=false
                    }.padding(13.dp))
                    HorizontalDivider()
                }
            }
        }
    }
}
@Composable private fun CurrencyMenu(lang:String,value:String,change:(String)->Unit) =
    SelectMenu(tr(lang,"currency"),currencies,value,change)
@Composable private fun ThemeMenu(lang:String,value:String,change:(String)->Unit) =
    SelectMenu(tr(lang,"theme"),listOf("system","light","dark"),value,change)

@Composable private fun JobCard(job:JSONObject,lang:String) {
    val uri=LocalUriHandler.current
    val rawLink=job.optString("apply_url",job.optString("source_url",""))
    val link=rawLink.takeIf {url->
        try { URL(url).protocol=="https" && URL(url).host.isNotBlank() }
        catch (_:Exception) {false}
    }
    val label=job.optString("company","").takeIf {it.isNotBlank()} ?: tr(lang,"unavailable")
    Card(modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(18.dp),
        colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
            Text(job.optString("title"),fontSize=18.sp,fontWeight=FontWeight.Bold)
            Text(label,color=MaterialTheme.colorScheme.secondary,fontWeight=FontWeight.SemiBold)
            Caption(countryFlag(job.optString("destination_country"))+" "+
                job.optString("candidate_required_location","—")+
                (if(job.optBoolean("remote",false)) " · Remote" else ""))
            Text(salaryLabel(job,lang),fontWeight=FontWeight.Bold,fontSize=16.sp)
            Caption(job.optString("source")+" · "+job.optString("published_at").take(10))
            if(link!=null) Button(onClick={uri.openUri(link)},modifier=Modifier.fillMaxWidth()) {
                Text(tr(lang,"apply"))
            }
        }
    }
}
@Composable private fun ApiResult(page:String,data:JSONObject,lang:String,origin:String,
    start:String,end:String,previous:Double?,current:Double?,amount:Double?,currency:String,fx:Map<String,JSONObject>) {
    when(page) {
        "salary" -> WageCard(data,lang,currency,fx)
        "compare" -> {
            data.optJSONObject("country_a")?.let {WageCard(it,lang,currency,fx)}
            data.optJSONObject("country_b")?.let {WageCard(it,lang,currency,fx)}
        }
        "exchange" -> {
            val rate=data.optDouble("units_per_eur",Double.NaN)
            if(rate.isFinite() && rate>0) {
                Metric("1 EUR",number(rate)+" "+data.optString("currency"),
                    data.optString("period")+" · "+data.optString("source"))
                if(amount!=null && amount>=0)
                    Metric(tr(lang,"value"),number(amount*rate)+" "+data.optString("currency"),
                        tr(lang,"fxnote"))
            } else Metric(tr(lang,"unavailable"),tr(lang,"nomatch"))
        }
        "inflation","power" -> {
            val arr=data.optJSONArray("history") ?: JSONArray()
            val byYear=(0 until arr.length()).mapNotNull {arr.optJSONObject(it)}.associateBy {it.optInt("year")}
            val first=start.toIntOrNull() ?: 0
            val last=end.toIntOrNull() ?: 0
            val annual=if(last>first && last-first<=100) (first+1..last).map { y ->
                byYear[y]?.optDouble("value",Double.NaN) ?: Double.NaN
            } else emptyList()
            if(annual.isNotEmpty() && annual.all {it.isFinite() && it>-100}) {
                val factor=annual.fold(1.0){acc,n -> acc*(1+n/100)}
                Metric(tr(lang,"inflation"),number((factor-1)*100)+" %",
                    start+" → "+end+" · World Bank")
                if(page=="power" && previous!=null && previous>0) {
                    val needed=previous*factor
                    Metric(if(lang=="pt") "Salário necessário" else "Required salary",
                        money(needed,currency),if(lang=="pt") "Para manter o poder de compra" else "To maintain purchasing power")
                    Metric(if(lang=="pt") "Aumento necessário" else "Required increase",
                        money(needed-previous,currency))
                    if(current!=null && current>=0 && needed>0) Metric(
                        if(lang=="pt") "Variação real do salário" else "Real salary change",
                        number((current/needed-1)*100)+" %")
                }
            } else Metric(tr(lang,"unavailable"),
                if(lang=="pt") "Não existem dados verificados para todos os anos selecionados." else "Verified data are missing for some selected years.")
        }
    }
}
@Composable private fun InsightsGraph(data:JSONObject,codes:List<String>,indicator:String,places:List<Place>) {
    val samples=codes.mapNotNull {code ->
        val item=data.optJSONObject(code) ?: return@mapNotNull null
        val v=item.optDouble("value",Double.NaN)
        if(item.optString("status")=="available" && v.isFinite() && v>=0) code to v else null
    }
    if(samples.isEmpty()) return
    val max=samples.maxOf {it.second}.coerceAtLeast(1.0)
    val colors=listOf(Color(0xFFF1D28C),Color(0xFF60CCB2),Color(0xFF8BABF0),Color(0xFFDAA1D3),Color(0xFFFF9D80))
    Column(Modifier.fillMaxWidth(),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        samples.forEachIndexed {i,(code,v) ->
            Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                Text(countryFlag(code)+" "+code,modifier=Modifier.width(58.dp),fontSize=12.sp)
                LinearProgressIndicator(progress={ (v/max).toFloat().coerceIn(0f,1f) },
                    modifier=Modifier.weight(1f).height(12.dp),
                    color=colors[i%colors.size],trackColor=MaterialTheme.colorScheme.surface)
                Text(number(v),fontSize=12.sp)
            }
        }
    }
}
private fun salaryCurrencies(data:JSONObject):List<String> {
    val out=mutableListOf<String>()
    val wage=data.optJSONObject("national_occupation_wage")
    wage?.optJSONArray("observations")?.let { a -> for(i in 0 until a.length()) a.optJSONObject(i)?.optString("currency")?.takeIf{it.isNotBlank()}?.let(out::add) }
    data.optJSONObject("national_major_group_context")?.optJSONArray("observations")?.let { a -> for(i in 0 until a.length()) a.optJSONObject(i)?.optString("currency")?.takeIf{it.isNotBlank()}?.let(out::add) }
    listOf("brazil_public_sector_entry","ireland_public_sector_entry","public_sector_entry").forEach { data.optJSONObject(it)?.optString("currency")?.takeIf{it.isNotBlank()}?.let(out::add) }
    return out
}
private fun preferredObservation(data:JSONObject?):JSONObject? {
    if(data?.optString("status")!="available") return null
    val a=data.optJSONArray("observations")
    if(a!=null && a.length()>0) {
        val rows=(0 until a.length()).mapNotNull{a.optJSONObject(it)}
        return rows.firstOrNull{it.optString("measure")=="median"} ?:
            rows.firstOrNull{it.optString("measure")=="median_hourly"} ?:
            rows.firstOrNull{it.optString("measure")=="mean"} ?:
            rows.firstOrNull{it.optString("measure")=="mean_hourly"} ?: rows.firstOrNull()
    }
    return data.takeIf{it.has("value")}
}
private fun groupObservation(data:JSONObject?):JSONObject? {
    if(data?.optString("status")!="available") return null
    preferredObservation(data)?.let{return it}
    val values=data.optJSONObject("values") ?: return null
    val keys=values.keys()
    while(keys.hasNext()) {
        val row=values.optJSONObject(keys.next())
        if(row?.optString("status")=="available" && row.has("value")) return row
    }
    return null
}
private fun publicObservation(data:JSONObject):JSONObject? =
    listOf("brazil_public_sector_entry","ireland_public_sector_entry","public_sector_entry")
        .mapNotNull{data.optJSONObject(it)}.firstOrNull{it.optString("status")=="available"}
private fun unitSuffix(unit:String,pt:Boolean)=when {
    unit.contains("/hour") -> if(pt)" / h" else " / h"
    unit.contains("/week") -> if(pt)" / sem" else " / wk"
    unit.contains("/month") || unit.contains("monthly") -> if(pt)" / mês" else " / mo"
    unit.contains("/year") || unit=="per_year" -> if(pt)" / ano" else " / yr"
    else -> ""
}
private fun convertedSalary(row:JSONObject?,preferred:String,fx:Map<String,JSONObject>):Pair<String,String>? {
    if(row==null) return null
    val value=row.optDouble("value",Double.NaN); val source=row.optString("currency")
    if(!value.isFinite() || source.isBlank()) return null
    val a=if(source=="EUR")1.0 else fx[source]?.optDouble("units_per_eur",Double.NaN)?:Double.NaN
    val b=if(preferred=="EUR")1.0 else fx[preferred]?.optDouble("units_per_eur",Double.NaN)?:Double.NaN
    if(source!=preferred && (!a.isFinite()||!b.isFinite()||a<=0||b<=0)) return null
    val shown=if(source==preferred)value else value*b/a
    val suffix=unitSuffix(row.optString("unit"),true)
    val original=if(source==preferred) "" else number(value)+" "+source+suffix
    return (number(shown)+" "+preferred+suffix) to original
}
@Composable private fun SalaryLegend(lang:String) {
    Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Caption(if(lang=="pt") "🟢 Profissão — observação oficial específica" else "🟢 Occupation — specific official observation")
        Caption(if(lang=="pt") "🟡 Grupo — referência ocupacional ampla" else "🟡 Group — broad occupational reference")
        Caption(if(lang=="pt") "🔵 Público — salário oficial de entrada" else "🔵 Public — official entry salary")
    }
}
@Composable private fun SalaryLayer(title:String,row:JSONObject?,preferred:String,fx:Map<String,JSONObject>,tint:Color,lang:String) {
    val converted=convertedSalary(row,preferred,fx)
    Surface(color=tint.copy(alpha=.13f),shape=RoundedCornerShape(12.dp),modifier=Modifier.fillMaxWidth()) {
        Column(Modifier.padding(11.dp),verticalArrangement=Arrangement.spacedBy(3.dp)) {
            Text(title,fontSize=11.sp,fontWeight=FontWeight.Bold,color=tint)
            Text(converted?.first ?: "—",fontSize=17.sp,fontWeight=FontWeight.Bold)
            if(!converted?.second.isNullOrBlank()) Caption((if(lang=="pt")"Original: " else "Original: ")+converted!!.second)
            val period=row?.optString("reference_period")?.takeIf{it.isNotBlank()} ?: row?.optString("period").orEmpty()
            if(period.isNotBlank()) Caption(period)
        }
    }
}
@Composable private fun GlobalSalaryCard(place:Place,data:JSONObject,lang:String,preferred:String,fx:Map<String,JSONObject>) {
    val exact=preferredObservation(data.optJSONObject("national_occupation_wage"))
    val group=groupObservation(data.optJSONObject("national_major_group_context"))
    val public=publicObservation(data)
    Card(shape=RoundedCornerShape(18.dp),colors=CardDefaults.cardColors(containerColor=MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
            Text(countryFlag(place.code)+" "+place.name,fontSize=17.sp,fontWeight=FontWeight.Bold)
            SalaryLayer(if(lang=="pt")"🟢 Profissão" else "🟢 Occupation",exact,preferred,fx,Color(0xFF087B62),lang)
            SalaryLayer(if(lang=="pt")"🟡 Grupo" else "🟡 Group",group,preferred,fx,Color(0xFF9A6A00),lang)
            SalaryLayer(if(lang=="pt")"🔵 Setor público" else "🔵 Public sector",public,preferred,fx,Color(0xFF1769A6),lang)
        }
    }
}

@Composable private fun RegionalWageCard(data:JSONObject,lang:String) {
    val region=data.optJSONObject("region")?.optString("selected").orEmpty()
    val code=data.optJSONObject("country")?.optString("code").orEmpty()
    if(region.isBlank() || code !in listOf("US","CA")) return
    val record=data.optJSONObject("regional_occupation_wage")
    val label=if(code=="CA") {
        if(lang=="pt") "Salário por província / território" else "Province / territory wage"
    } else if(lang=="pt") "Salário por Estado" else "State wage"
    val name=if(code=="CA") record?.optString("province_name")?.takeIf{it.isNotBlank()} ?: region
        else record?.optString("state_name")?.takeIf{it.isNotBlank()} ?: region
    if(record?.optString("status")!="available") {
        Metric(label+" · "+name,
            if(lang=="pt") "Dados regionais indisponíveis" else "Regional data unavailable",
            if(lang=="pt") "Não foi estimado um valor com base na média nacional."
                else "No value was inferred from the national wage.")
        return
    }
    val metrics=record.optJSONObject("metrics")
    val unit=if(code=="CA") record.optString("unit") else
        if(metrics?.isNull("a_median")==false || metrics?.isNull("a_mean")==false) "USD/year" else "USD/hour"
    val median=if(code=="CA") metrics?.optDouble("median",Double.NaN) ?: Double.NaN
        else metrics?.optDouble(if(unit=="USD/year") "a_median" else "h_median",Double.NaN) ?: Double.NaN
    val mean=if(code=="CA") metrics?.optDouble("mean",Double.NaN) ?: Double.NaN
        else metrics?.optDouble(if(unit=="USD/year") "a_mean" else "h_mean",Double.NaN) ?: Double.NaN
    val preferredValue=if(median.isFinite() && median>0) median else mean
    val measure=if(median.isFinite() && median>0)
        if(lang=="pt") "Mediana" else "Median"
        else if(lang=="pt") "Média" else "Mean"
    val currency=if(code=="CA") "CAD" else "USD"
    val suffix=if(unit.endsWith("/year")) (if(lang=="pt") " / ano" else " / year")
        else (if(lang=="pt") " / hora" else " / hour")
    val period=record.optString("reference_period")
    if(preferredValue.isFinite() && preferredValue>0) {
        Metric(label+" · "+name,money(preferredValue,currency)+suffix,
            measure+" · "+period+" · "+(if(lang=="pt")
                "Bruto estatístico; não representa salário líquido."
                else "Published gross statistic; not take-home pay."))
    } else {
        Metric(label+" · "+name,
            if(lang=="pt") "Salário não publicado" else "Wage not published",
            period)
    }
}

@Composable private fun WageCard(data:JSONObject,lang:String,preferred:String,fx:Map<String,JSONObject>) {
    val c=data.optJSONObject("country")
    val code=c?.optString("code") ?: ""
    val name=c?.optString("name") ?: code
    RegionalWageCard(data,lang)
    if(code=="IN") {
        val plfs=data.optJSONObject("india_plfs_employee_earnings_context")
        if(plfs?.optString("status")=="available") {
            val monthly=plfs.optDouble("national_average",Double.NaN)
            if(monthly.isFinite() && monthly>0) {
                Metric(
                    if(lang=="pt") "Índia · contexto nacional PLFS" else "India · national PLFS context",
                    money(monthly,"INR")+(if(lang=="pt") " / mês" else " / month"),
                    if(lang=="pt")
                        "Média de todos os trabalhadores assalariados regulares (2025). Não representa o salário desta profissão nem o salário líquido."
                    else "Average for all regular wage/salaried workers (2025). Not this occupation's pay or take-home income."
                )
            }
        }
    }
    if(code=="IN") {
        val group=data.optJSONObject("india_nco2015_professional_group_context")
        if(group?.optString("status")=="available") {
            val sample=group.optJSONObject("observation")
            val monthly=sample?.optDouble("value",Double.NaN) ?: Double.NaN
            if(monthly.isFinite() && monthly>=0) {
                val groupLabel=group.optString("nco2015_group_label")
                val codeNco=group.optString("nco2015_group")
                Metric(
                    if(lang=="pt") "Índia · referência do grupo NCO" else "India · NCO group context",
                    money(monthly,"INR")+(if(lang=="pt") " / mês" else " / month"),
                    "NCO "+codeNco+" · "+groupLabel+"\n"+
                        (if(lang=="pt")
                            "Média ponderada do grupo profissional em 2025; não é o salário específico desta profissão."
                        else "Weighted 2025 occupational-group average; not this specific profession's wage.")
                )
            }
        }
    }
    val annual=data.optJSONObject("annual_presentation")
    if(annual?.optString("status")!="available") {
        val group = data.optJSONObject("national_major_group_context")
        val hasGroup = group?.optString("status")=="available"
        val detail = if(lang=="pt")
            if(hasGroup) "Não existe salário validado para esta profissão. Há apenas uma média do grande grupo ISCO-08, que não é o salário de médico, enfermeiro ou psicólogo."
            else "Não existe salário validado para esta profissão neste país."
        else if(hasGroup) "No verified wage for this occupation. The available ISCO-08 major-group average is not a salary for this specific job."
        else "No verified occupation-specific wage for this country."
        Metric(countryFlag(code)+" "+name,
            if(lang=="pt") "Salário profissional indisponível" else "Occupation wage unavailable",
            detail)
        return
    }
    val value=annual.optDouble("value",Double.NaN)
    val local=annual.optString("currency")
    if(!value.isFinite() || local.isBlank()) {
        Metric(countryFlag(code)+" "+name,tr(lang,"nomatch")); return
    }
    val a=if(local=="EUR") 1.0 else fx[local]?.optDouble("units_per_eur",Double.NaN) ?: Double.NaN
    val b=if(preferred=="EUR") 1.0 else fx[preferred]?.optDouble("units_per_eur",Double.NaN) ?: Double.NaN
    val dateA=fx[local]?.optString("period").orEmpty()
    val dateB=fx[preferred]?.optString("period").orEmpty()
    val canConvert=local==preferred || (a.isFinite() && b.isFinite() && a>0 && b>0 &&
        (dateA.isBlank() || dateB.isBlank() || dateA==dateB))
    val suffix=if(annual.optString("unit")=="per_year") if(lang=="pt") " / ano" else " / year" else ""
    val displayed=if(local==preferred) value else value*b/a
    val label=if(data.optJSONObject("national_occupation_wage")?.optString("status")=="available")
        if(lang=="pt") "Salário profissional" else "Occupation wage"
    else if(lang=="pt") "Referência do grupo profissional" else "Occupational group reference"
    val source=annual.optString("reference_period")+" · "+annual.optString("source")
    if(canConvert) Metric(countryFlag(code)+" "+name,money(displayed,preferred)+suffix,
        label+" · "+source+
        (if(local!=preferred) "\n"+(if(lang=="pt") "Moeda local: " else "Local currency: ")+money(value,local)+suffix else ""))
    else Metric(countryFlag(code)+" "+name,money(value,local)+suffix,
        source+" · "+(if(lang=="pt") "Conversão indisponível" else "Conversion unavailable"))
}
