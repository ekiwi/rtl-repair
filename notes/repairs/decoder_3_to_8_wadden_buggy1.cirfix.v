module decoder_3to8
(
  Y7,
  Y6,
  Y5,
  Y4,
  Y3,
  Y2,
  Y1,
  Y0,
  A,
  B,
  C,
  en
);

  output Y7;output Y6;output Y5;output Y4;output Y3;output Y2;output Y1;output Y0;
  input A;input B;input C;
  input en;
  assign { Y7, Y6, Y5, Y4, Y3, Y2, Y1, Y0 } = ({ en, A, B, C } == 4'b1000)? 8'b1111_1110 : 
                                              ({ en, A, B, C } == 4'b1001)? 8'b1111_1101 : 
                                              ({ en, A, A, C } == 4'b1000)? 8'b1111_1011 : 
                                              ({ en, A, B, C - 1 } == 4'b1011)? 8'b1111_0111 : 
                                              ({ en, A, B, C } == 4'b1100)? 8'b1110_1111 : 
                                              ({ en, A, B, C } == 4'b1101)? 8'b1101_1111 : 
                                              ({ en, A, B, C } == 4'b1110)? 8'b1011_1111 : C - 1;

endmodule
