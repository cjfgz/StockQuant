Sub 水果销售统计()
    ' 清除工作表内容
    Sheets("Sheet1").Cells.Clear
    
    ' 设置表头
    With Sheets("Sheet1")
        .Range("A1") = "水果名称"
        .Range("B1") = "单价(元)"
        .Range("C1") = "销售数量(斤)"
        .Range("D1") = "销售金额(元)"
        .Range("E1") = "销售日期"
        
        ' 设置表头格式
        .Range("A1:E1").Font.Bold = True
        .Range("A1:E1").Interior.Color = RGB(200, 200, 200)
        
        ' 添加水果数据
        ' 第一种水果
        .Range("A2") = "苹果"
        .Range("B2") = 5.5
        .Range("C2") = 100
        .Range("D2").Formula = "=B2*C2"
        .Range("E2") = Date
        
        ' 第二种水果
        .Range("A3") = "香蕉"
        .Range("B3") = 4.8
        .Range("C3") = 80
        .Range("D3").Formula = "=B3*C3"
        .Range("E3") = Date
        
        ' 第三种水果
        .Range("A4") = "橙子"
        .Range("B4") = 6.5
        .Range("C4") = 120
        .Range("D4").Formula = "=B4*C4"
        .Range("E4") = Date
        
        ' 第四种水果
        .Range("A5") = "梨"
        .Range("B5") = 5.2
        .Range("C5") = 90
        .Range("D5").Formula = "=B5*C5"
        .Range("E5") = Date
        
        ' 第五种水果
        .Range("A6") = "葡萄"
        .Range("B6") = 8.8
        .Range("C6") = 60
        .Range("D6").Formula = "=B6*C6"
        .Range("E6") = Date
        
        ' 添加合计行
        .Range("A7") = "合计"
        .Range("D7").Formula = "=SUM(D2:D6)"
        .Range("A7:E7").Font.Bold = True
        .Range("A7:E7").Interior.Color = RGB(220, 220, 220)
        
        ' 设置列宽
        .Columns("A:E").AutoFit
        
        ' 设置数字格式
        .Range("B2:B6").NumberFormat = "0.00"
        .Range("D2:D7").NumberFormat = "0.00"
        .Range("E2:E6").NumberFormat = "yyyy-mm-dd"
        
        ' 添加边框
        .Range("A1:E7").Borders.LineStyle = xlContinuous
        
        ' 设置对齐方式
        .Range("A1:E7").HorizontalAlignment = xlCenter
        .Range("A2:A6").HorizontalAlignment = xlLeft
    End With
    
    ' 添加图表
    Dim cht As Chart
    Set cht = Sheets("Sheet1").Shapes.AddChart2.Chart
    
    With cht
        .ChartType = xlColumnClustered
        .SetSourceData Source:=Sheets("Sheet1").Range("A1:D6")
        .HasTitle = True
        .ChartTitle.Text = "水果销售金额统计"
        .Parent.Left = Sheets("Sheet1").Range("G2").Left
        .Parent.Top = Sheets("Sheet1").Range("G2").Top
        .Parent.Width = 400
        .Parent.Height = 300
    End With
End Sub 