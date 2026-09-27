package com.earnwage.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
    var requestPage by remember { mutableStateOf("") }
    var response by remember { mutableStateOf<JSONObject?>(null) }
    var error by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    fun navigate(next:String) { page=next; request=""; response=null; error=""; loading=false }
    fun search(path:String) { response=null; error=""; requestPage=page; request=path }
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
    LaunchedEffect(request) {
        if(request.isNotBlank()) {
            val target=requestPage
            loading=true
            try {
                val data=api(request)
                if(page==target) response=data
            } catch(e:Exception) {
                if(page==target) error=e.message ?: "Network error"
            } finally { if(page==target) loading=false }
        }
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
                            item { Feature("⇄",tr(lang,"compare"),tr(lang,"wagesnote")) {navigate("compare")} }
                            item { Feature("▣",tr(lang,"jobs"),tr(lang,"jobnote")) {navigate("jobs")} }
                            item { Feature("◈",tr(lang,"salary"),tr(lang,"official")) {navigate("salary")} }
                            item { Feature("⊕",tr(lang,"tools"),tr(lang,"more")) {navigate("tools")} }
                            item { Caption(countryFlag(country)+" "+(countries.find { it.code==country }?.name ?: country)+
                                " · "+tr(lang,"currency")+": "+currency+" · API "+apiVersion) }
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
                            item { Caption(tr(lang,"wagesnote")+"
"+tr(lang,"nethint")) }
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
                            item { Caption(tr(lang,"jobnote")) }
                        }
                        "tools" -> {
                            item { Heading(tr(lang,"tools")) }
                            item { Feature("↗",tr(lang,"inflation"),tr(lang,"official")) {navigate("inflation")} }
                            item { Feature("◈",tr(lang,"power"),tr(lang,"powernote")) {navigate("power")} }
                            item { Feature("⇆",tr(lang,"exchange"),tr(lang,"fxnote")) {navigate("exchange")} }
                        }
                        "inflation","power" -> {
                            item { Heading(tr(lang,if(page=="inflation") "inflation" else "power")) }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it} }
                            item { NumberBox(tr(lang,"yearfrom"),fromYear) {fromYear=it} }
                            item { NumberBox(tr(lang,"yearto"),toYear) {toYear=it} }
                            if(page=="power") {
                                item { NumberBox(tr(lang,"initial"),previous) {previous=it} }
                                item { NumberBox(tr(lang,"current"),current) {current=it} }
                                item { NumberBox("Inflation % (manual / opcional)",enteredInflation) {enteredInflation=it} }
                            }
                            item {
                                Button(onClick={search("/v1/inflation/"+country)},
                                    enabled=(fromYear.toIntOrNull() ?: 0)<(toYear.toIntOrNull() ?: 0),
                                    modifier=Modifier.fillMaxWidth()) {Text(tr(lang,"calculate"))}
                            }
                            if(page=="power") item {
                                val inflation=enteredInflation.toDoubleOrNull()
                                val a=previous.toDoubleOrNull()
                                val b=current.toDoubleOrNull()
                                if(inflation!=null && inflation>-100 && a!=null && a>0 && b!=null && b>=0) {
                                    val required=a*(1+inflation/100)
                                    Metric("Manual inflation (user entered)",number(inflation)+" %","Not an official series")
                                    Metric("Income required",number(required),"Same period and currency as entered")
                                    Metric("Real income change",number((b/required-1)*100)+" %","Based solely on entered inflation")
                                }
                            }
                            item { Caption(tr(lang,"powernote")) }
                        }
                        "exchange" -> {
                            item { Heading(tr(lang,"exchange")) }
                            item { CurrencyMenu(lang,currency) {currency=it} }
                            item { NumberBox(tr(lang,"amount"),amount) {amount=it} }
                            item {
                                Button(onClick={
                                    if(currency=="EUR") response=JSONObject()
                                        .put("currency","EUR").put("units_per_eur",1.0).put("source","Identity EUR/EUR")
                                    else search("/v1/exchange-rates/"+currency)
                                },modifier=Modifier.fillMaxWidth()) {Text(tr(lang,"calculate"))}
                            }
                            item { Caption(tr(lang,"fxnote")) }
                        }
                        "settings" -> {
                            item { Heading(tr(lang,"settings")) }
                            item { LanguageMenu(lang) {lang=it} }
                            item { PlaceMenu(tr(lang,"country"),countries,country) {country=it} }
                            item { CurrencyMenu(lang,currency) {currency=it} }
                            item { ThemeMenu(lang,appearance) {appearance=it} }
                            item { Caption(tr(lang,"settingsnote")+"
"+tr(lang,"countryhint")) }
                            item { Feature("ⓘ",tr(lang,"about"),tr(lang,"data")) {navigate("about")} }
                        }
                        "about" -> {
                            item { Heading(tr(lang,"about")) }
                            item { Metric("EarnWage","v"+BuildConfig.VERSION_NAME,
                                "com.earnwage.app · Gil Pereira") }
                            item { Metric(tr(lang,"apiversion"),apiVersion,BuildConfig.API_BASE_URL) }
                            item { Caption("Your salary. Your world.
14 countries · 40 occupations · 7 interface languages") }
                            item { Caption("Eurostat · ECB · ILOSTAT · BLS · Canada Job Bank · Remotive · Arbeitnow · Himalayas · Jobicy · Remote OK · Greenhouse · Lever · Ashby") }
                            item { Caption(tr(lang,"wagesnote")+"
"+tr(lang,"nethint")+"
"+tr(lang,"jobnote")) }
                        }
                    }
                    if(loading) item { CircularProgressIndicator() }
                    if(error.isNotBlank()) item {
                        Metric(tr(lang,"unavailable"),error,tr(lang,"retry"))
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
                            item { ApiResult(page,data,lang,country,fromYear,toYear,previous.toDoubleOrNull(),current.toDoubleOrNull(),amount.toDoubleOrNull()) }
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
    start:String,end:String,previous:Double?,current:Double?,amount:Double?) {
    when(page) {
        "salary" -> WageCard(data,lang)
        "compare" -> {
            data.optJSONObject("country_a")?.let {WageCard(it,lang)}
            data.optJSONObject("country_b")?.let {WageCard(it,lang)}
            Caption(tr(lang,"nethint"))
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
            val arr=data.optJSONArray("series") ?: JSONArray()
            val observations=(0 until arr.length()).mapNotNull{arr.optJSONObject(it)}
            val first=observations.firstOrNull{it.optString("period").startsWith(start)}
            val last=observations.lastOrNull{it.optString("period").startsWith(end)}
            val a=first?.optDouble("index",Double.NaN) ?: Double.NaN
            val b=last?.optDouble("index",Double.NaN) ?: Double.NaN
            if(a.isFinite() && b.isFinite() && a>0 && b>0 &&
                first!!.optString("period")<last!!.optString("period")) {
                val factor=b/a
                Metric(tr(lang,"inflation"),number((factor-1)*100)+" %",
                    first.optString("period")+" → "+last.optString("period")+" · "+data.optString("source"))
                if(page=="power" && previous!=null && previous>0) {
                    val needed=previous*factor
                    Metric("Income required",number(needed),"Verified national inflation · original income units")
                    if(current!=null && current>=0) Metric("Real income change",
                        number((current/needed-1)*100)+" %","Based on national inflation, not city costs")
                }
            } else Metric(tr(lang,"unavailable"),tr(lang,"nomatch"),tr(lang,"powernote"))
        }
    }
}
@Composable private fun WageCard(data:JSONObject,lang:String) {
    val c=data.optJSONObject("country")
    val name=(c?.optString("code") ?: "")+" · "+(c?.optString("name") ?: "")
    val annual=data.optJSONObject("annual_presentation")
    val exact=data.optJSONObject("national_occupation_wage")?.optString("status")=="available"
    val valid=annual?.optString("status")=="available"
    if(valid) {
        val value=annual!!.optDouble("value",Double.NaN)
        if(value.isFinite()) {
            Metric(countryFlag(c?.optString("code") ?: "")+" "+name,
                number(value)+" "+annual.optString("currency")+
                    (if(annual.optString("unit")=="per_year") " / year" else ""),
                (if(exact) tr(lang,"profession") else "ISCO-08 major-group context (NOT profession salary)")+
                    " · "+annual.optString("reference_period")+" · "+annual.optString("source"))
            Caption(annual.optString("note"))
        } else Metric(name,tr(lang,"nomatch"))
    } else Metric(name,tr(lang,"nomatch"))
    Caption(tr(lang,"wagesnote"))
}
