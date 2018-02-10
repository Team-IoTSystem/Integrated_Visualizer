'use strict';

var svg = d3.select("svg")

//データセットの作成
let dataLength;
dataLength = 12;
var data = d3.range(dataLength).map(function () {
    return d3.range(dataLength).map(function () {
        return Math.floor(Math.random() * dataLength)
    })
});
console.log(data);

//カラースケール
var color = d3.scale.category20();

//chordジェネレータ生成
var chord = d3.layout.chord()
    .padding(0.1)//データ束間の隙間
    .matrix(data);

//chord全体
var chordGroup = svg.append('g')
    .attr("transform", "translate(" + [400, 400] + ")");

//外円
chordGroup.selectAll("path.groups")
    .data(chord.groups)
    .enter()
    .append("path")
    .attr({
        "fill": function (d) {
            return color(d.index);
        },
        "stroke": function (d) {
            return color(d.index);
        },
        "d": d3.svg.arc().innerRadius(350).outerRadius(400),
    });


//データ間のリンク
chordGroup.selectAll("path.chord")
    .data(chord.chords)
    .enter()
    .append("path")
    .attr({
        "fill": function (d) {
            return color(d.source.index);
        },
        "d": d3.svg.chord().radius(400),
        "opacity": 0.5
    })
    .on('mouseover', function () {
        d3.select(this).attr({
            'fill': "red",
            "opacity": 1
        });
    })
    .on('mouseout', function () {
        d3.select(this).attr({
            'fill': function (d) {
                return color(d.source.index);
            },
            "opacity": 0.5
        });
    });